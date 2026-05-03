from knowledge.processor.import_process.base import BaseNode, setup_logging, T
from knowledge.processor.import_process.state import ImportGraphState
from knowledge.processor.import_process.exceptions import ValidationError
from knowledge.processor.import_process.config import get_config



import re 
import os
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentSplitNode(BaseNode):
    """
    文档切分节点类
    """
    name = "document_split_node"

    def process(self, state: T):
        # 加载 ----> 打散(1.嵌入模型语义更准确 2.注入元数据 3.多路召回 4.性能、成本高 -----> 减少LLM幻觉，提高检索质量) ----> 组合

        # 1. 获取参数
        md_content, file_title, max_content_length, min_content_length = self._get_inputs(state)

        # 2. 根据标题切割(核心)
        sections = self._split_by_headings(md_content, file_title)

        # 3. 处理(切分和合并)
        final_chunks = self._split_and_merge(sections, max_content_length, min_content_length)

        # 4. 组装
        chunks = self._assemble_chunks(final_chunks)

        # 5. 更新state：chunks
        state["chunks"] = chunks

        # 6. 日志统计
        self._log_summary(md_content, chunks, max_content_length)

        # 7. 备份
        state["chunks"] = chunks
        self._backup_chunks(state, chunks)

        return state
    
        # ------------------------------------------------------------------ #
        #                       日志 & 备份                                   #
        # ------------------------------------------------------------------ #

    def _log_summary(self, raw_content: str, chunks: list[dict], max_length: int):
        """输出切分统计信息"""
        self.log_step("step5", "输出统计")

        lines_count = raw_content.count("\n") + 1
        self.logger.info(f"原文档行数: {lines_count}")
        self.logger.info(f"最终切分章节数: {len(chunks)}")
        self.logger.info(f"最大切片长度: {max_length}")

        if chunks:
            self.logger.info("章节预览:")
            for i, sec in enumerate(chunks[:5]):
                title = sec.get("title", "")[:30]
                self.logger.info(f"  {i + 1}. {title}...")
            if len(chunks) > 5:
                self.logger.info(f"  ... 还有 {len(chunks) - 5} 个章节")    

    def _backup_chunks(self, state: ImportGraphState, sections: list[dict]):
        """将切分结果备份到 JSON 文件"""
        self.log_step("step6", "备份切片")

        local_dir = state.get("file_dir", "")
        if not local_dir:
            self.logger.debug("未设置 file_dir,跳过备份")
            return

        try:
            os.makedirs(local_dir, exist_ok=True)
            output_path = os.path.join(local_dir, "chunks.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(sections, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已备份到: {output_path}")

        except Exception as e:
            self.logger.warning(f"备份失败: {e}")    

    def _get_inputs(self, state: ImportGraphState) -> tuple[str, str, int]:

        self.log_step("step1", "切分文档参数 校验并获取")


        config = get_config()
        md_content = state.get("md_content")

        # 2. 统一换行符
        if md_content:
            md_content.replace("\r\n", "\n").replace("\r", "\n")

        # 3. 获取文件的标题
        file_title = state.get("file_title")

        # 4. 校验最大最小值
        if config.max_content_length <= 0 or config.min_content_length <= 0 or config.max_content_length <= config.min_content_length:
            raise ValidationError(f"切片长度参数校验失败")
        return md_content, file_title, config.max_content_length, config.min_content_length

    def _split_by_headings(self, md_content: str, file_title: str) -> list[dict]:
        """
        根据md所有级别标题切割文档内容
        Args:
            md_content: 文档内容
            file_title: 文档名字
        Returns:
            tuple[list[dict], bool]
            list[dict]: sections
            bool: 是否有标题
            {
                "title":"# 第一章",
                "body": "正文内容....",
                "file_title": "万用表",
                "parent_title": "# 第一章" 父标题会更新
            }
        """
        self.log_step("step2", "根据标题切割文档内容")
        # 1. 定义变量
        in_fence = False
        body_lines = []
        sections = []
        current_title = "" # 全局变量
        current_level = 0
        hierarchy = [""] * 7 # 第一个不使用 只使用六个索引

        # 2. 定义正则表达式（group1:标题的语法符号 # [最少一个# 最多六个#]）
        heading_re = re.compile(r"^\s*(#{1,6})\s+(.+)")

        # 3. 切分
        content_lines = md_content.split("\n")

        def _flush():
            """
            封装section对象
            Return:
                dict: section对象
            """
            body = "\n".join(body_lines)

            if current_title or body:
                parent_title = ""
                for i in range(current_level - 1, 0, -1):
                    if hierarchy[i]:
                        parent_title = hierarchy[i]
                        break

                if not parent_title:
                    parent_title = current_title if current_title else file_title

                return sections.append({
                    "title": current_title if current_title else file_title,
                    "body": body,
                    "file_title": file_title,
                    "parent_title": parent_title
                })

        for content_line in content_lines:
            # 3.1 判断当前行是否存在代码块围栏
            if content_line.strip().startswith("```") or content_line.strip().startswith("~~~"):
                in_fence = not in_fence

            match = heading_re.match(content_line) if not in_fence else None
            if match:
                # 当前行是标题
                _flush()
                level = len(match.group(1)) # 当前标题的级别
                current_level = level # 当前标题的级别 _flush用
                current_title = content_line
                hierarchy[level] = current_title # 当前标题的名字

                for i in range(level +1, 7): # 清空
                    hierarchy[i] = ""

                # 存储当前遍历的标题
                body_lines = []

            # 除了标题行全部收集起来
            else:
                body_lines.append(content_line)

        _flush()
        return sections
    
    def _split_and_merge(self, sections: list[dict], max_content_length: int, min_content_length: int) -> list[dict]:
        """
        切分和合并section
        Args:
            sections: 根据以及标题切分后的section
            max_content_length: 每一个section的content内容[title+body]长度最多不能超过指定 将标题注入到内容中(标题注入：明确定位这一块的归属)
            min_content_length: 每一个section的content内容[title+body]长度如果比指定的min_content_length小 则与它的同源合并
        Returns:
            list[dict]: 合并后的section
        """
        self.log_step("step3", "切分和合并section")
        # 切分
        current_sections = []

        for section in sections:
            current_sections.extend(self._spilt_long_section(section, max_content_length))

        # 合并
        final_sections = self._merge_short_sections(current_sections, min_content_length)

        return final_sections

    def _spilt_long_section(self, section: dict, max_content_length: int) -> list[dict]:
        """
        切分section
        Args:
            sections: 根据以及标题切分后的section
            max_content_length: 每一个section的content内容[title+body]长度最多不能超过指定 将标题注入到内容中(标题注入：明确定位这一块的归属)
        Returns:
            list[dict]: 切分后的section
        """
        self.log_step("step3.1", "切分section")
        
        # 1. 获取sections对象属性
        title = section.get("title")
        body = section.get("body")
        file_title = section.get("file_title")
        parent_title = section.get("parent_title")

        # 2. 对标题做校验
        title_max_length = 50
        if len(title) > title_max_length:
            self.logger.warning(f"文件{file_title}对应的{title}长度过长")
            title = title[:title_max_length]

        # 3. 拼接title的前缀
        title_prefix = f"{title}\n\n"

        # 4. 计算总长度(len（title_prefix） + len(body))
        total_length = len(title_prefix) + len(body)

        # 5. 判断
        if total_length <= max_content_length:
            return [section]
        
        # 6. 计算body可用的长度
        available_body_length = max_content_length - len(title_prefix)

        if available_body_length <= 0:
            return [section]
        
        # 7. 切分body
        # 定义递归的文档切分器
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = available_body_length,
            chunk_overlap = 0,
            separators=["\n\n", "\n", "。","；", "！", "？",";", "!", "?", ".", "！", "？", " ", ""],
            keep_separator= False
        )
        # 切割
        texts = text_splitter.split_text(body)

        # 判断(小于0时为body没有 等于1时为body很少)
        if len(texts) <= 1:
            return [section]
        
        sub_sections = []
        for index, text in enumerate(texts):
            sub_sections.append(
                {
                    "title": title + f"-{index + 1}",
                    "body": text,
                    "file_title": file_title,
                    "parent_title": parent_title,
                    "part": f'{index + 1}'
                }
            )
        
        return sub_sections

    def _merge_short_sections(self, sections: list[dict], min_content_length: int) -> list[dict]:
        """
        合并section(使用贪心累加算法)

        两个局限性
        1. 可能撑爆最小的阈值
        2. 可能会剩下一个孤儿块

        Args:
            sections: 切分后的section
            min_content_length: 每一个section的content内容[title+body]长度如果比指定的min_content_length小 则与它的同源合并
        Returns:
            list[dict]: 合并后的section
        """
        current_section = sections[0]
        final_sections = []

        for next_section in sections[1:]:
            # 同源
            same_parent = (current_section['parent_title'] == next_section['parent_title'])
            if same_parent and len(current_section.get('body')) < min_content_length:
                current_section['body'] = (current_section.get('body').rstrip() +"\n\n" +  next_section.get('body').lstrip())

                # 更新current_title
                current_section['title'] = current_section["parent_title"]

                current_section['part'] = 0
            
            else:
                # 1. 将原来的current_section进行封箱
                final_sections.append(current_section)
                # 2. 更新next_section
                current_section = next_section

        # 3. 最后将current_section也封箱
        final_sections.append(current_section)
        

        # 对所有section的part做处理(为每一个父标题设置对应的part计数器)
        part_counter = {}
        result = []
        for final_section in final_sections:
            if "part" in final_section:
                parent_title = final_section.get("parent_title")
                part_counter[parent_title] = part_counter.get(parent_title, 0) + 1
                new_part = part_counter[parent_title]
                final_section['part'] = new_part

                final_section["title"] = final_section["title"] + "-" + str(new_part)

            result.append(final_section)

        return result
    
    def _assemble_chunks(self, final_chunks: list[dict]) -> list[dict]:
        """
        组装chunks

        Args:
            final_chunks: 合并后的section
        Returns:
            list[dict]: 组装后的chunk
        """
        self.log_step("step4", "组装最终的切片信息。。。")
        chunks = []
        for chunk in final_chunks:
            # 1. 获取chunk的信息
            title = chunk.get("title")
            body = chunk.get("body")
            file_title = chunk.get("file_title")
            parent_title = chunk.get("parent_title")
            # content = f"{title}\n{body}"

            # 2. 构建最终chunk对象
            assemble_chunk = {
                "title": title,
                "body" : body,
                "file_title": file_title,
                "parent_title": parent_title,
                # "content": content,
            }

            # 3. 判断part是否存在
            if "part" in chunk:
                assemble_chunk["part"] = chunk.get("part")

            chunks.append(assemble_chunk)    

        return chunks
            
            
if __name__ == "__main__":
    setup_logging()
    document_node = DocumentSplitNode()
    # 构造状态字典
    file_path = r"D:\pycharm\project\shopkeeper_brain\scripts\processed\语文文言文原文_解析\hybrid_auto\语文文言文原文_解析.md"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    state = {
        "file_title": "文言文",
        "md_content": content,
        "file_dir": r"D:\pycharm\project\shopkeeper_brain\scripts\processed\语文文言文原文_解析\json_file",
    }
    print(document_node.process(state))
