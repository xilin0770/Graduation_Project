from knowledge.processor.query_process.state import QueryGraphState
from knowledge.processor.query_process.base import BaseNode
from knowledge.utils.milvus_util import create_hybrid_search_requests, execute_hybrid_search_query
from knowledge.utils.bge_me_embedding_util import get_beg_m3_embedding_model, generate_hybrid_embedding
from knowledge.utils.milvus_util import get_milvus_client, create_hybrid_search_requests, execute_hybrid_search_query
from knowledge.processor.query_process.exceptions import StateFieldEooror
from knowledge.utils.llm_client import get_llm_client
from knowledge.prompts.query.match_query_prompt import CLASSICAL_HYDE_PROMPT_TEMPLATE

from langchain_core.messages import SystemMessage, HumanMessage
import json

class HyDeSearchNode(BaseNode):
    name = "hyde_search_node"

    def process(self, state: QueryGraphState) -> QueryGraphState:

        # 1. 参数校验
        validated_query, validated_entity_names = self._validate_query_inputs(state)

        # 2. 生成假设性文档
        hy_document = self._generate_hy_document(validated_query, validated_entity_names)

        # 3. 获取嵌入模型以及milvus客户端
        embedding_model = get_beg_m3_embedding_model()
        milvus_client = get_milvus_client()

        if  not embedding_model or not milvus_client:
            return state

        # 4. 对假设性文档的嵌入
        embedding_document = f"{validated_query}\n {hy_document}"
        embedding_result = generate_hybrid_embedding(embedding_documents=[embedding_document], embedding_model=embedding_model)
        if not embedding_result:
            return state
        
        # 5. 获取entity_name的过滤表达式
        # entity_name_filter_expr = self._entity_name_filter(validated_entity_names)
        
        # 6. 创建混合搜索请求
        hybird_search_requests = create_hybrid_search_requests(
            dense_vector=embedding_result["dense"][0],
            sparse_vector=embedding_result["sparse"][0],
            # expr=entity_name_filter_expr
        )

        # 7. 执行混合搜索请求
        reps = execute_hybrid_search_query(
            milvus_client = milvus_client,
            collection_name= "test_chunks_collection",
            search_requests = hybird_search_requests,
            ranker_weights=(0.5, 0.5),
            norm_score=True,
            output_fields=["chunk_id", "body", "title"]
        )

        if not reps or not reps[0]:
            return state
        
        # 8. 更新state的hyde_embedding_chunks
        state["hyde_embedding_chunks"] = reps[0]

        # 9. 返回更新后的state
        return state


    def _validate_query_inputs(self, state: QueryGraphState) -> tuple[str, list[str]]:
        """校验查询输入参数。

        Args:
            state: 查询状态对象。

        Returns:
            校验后的查询字符串和商品名称列表。

        Raises:
            StateFieldEooror: 状态字段缺失或无效。
        """
        # 1. 获取state的rewritten_query字段
        rewritten_query = state.get("rewritten_query", "")

        # 2. 获取state中的entity_names字段
        entity_names = state.get("entity_names", "")

        # 3. 校验
        if not rewritten_query or not isinstance(rewritten_query, str):
            raise StateFieldEooror(field_name="rewritten_query", node_name=self.name, expected_type = str)
        
        if not entity_names or not isinstance(entity_names, list):
            raise StateFieldEooror(field_name="entity_names", node_name=self.name, expected_type = list)
        
        # 4. 返回
        return rewritten_query, entity_names

    def _generate_hy_document(self, query: str, validated_entity_names: list[str]) -> str:

        # 1. 获取llm的客户端
        llm_client = get_llm_client()

        if llm_client is None:
            return ""
        
        # 3. 获取系统提示词
        user_prompt = CLASSICAL_HYDE_PROMPT_TEMPLATE.format(word_hint = validated_entity_names, rewritten_query = query)
        system_prompt = f"你是一位顶级的古典文学领域的学者，主要擅长文言文解读、古诗词鉴赏、经典文献阐释"
        try:
            # 4. 获取AIMessage
            llm_response = llm_client.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            # 5. 获取内容
            llm_response_content = getattr(llm_response, "content", "").strip()

            # 6. 判断是否存在
            if not llm_response_content:
                return ""
            
            return llm_response_content
        except Exception as e:
            self.logger.error(f"调用LLM调用失败: {e}")
            return ""
        
    def _entity_name_filter(self, entity_names: list[str]) -> str:
        """构建商品名称过滤表达式。

        Args:
            entity_names: 商品名称列表。

        Returns:
            商品名称过滤表达式。
        """
        # conditions = [f"entity_name in ['{name}']" for name in entity_names]
        conditions = [f"entity_name like '%{name}%'" for name in entity_names]
        return "(" + " OR ".join(conditions) + ")"
    

if __name__ == "__main__":
    # 测试代码
    state = {
        'original_query': '18年的Ⅰ卷中“鲁芝字世英，扶风郿人也，世有名德，为西州豪族。”中的“也”有什么作用？',
        'rewritten_query': '请问“也”字在文言文句子“鲁芝字世英，扶风郿人也，世有名德，为西州豪族。”中有什么作用？',
        'entity_names': ['也']
    }
    node = HyDeSearchNode()
    new_state = node.process(state)

    for r in new_state.get("hyde_embedding_chunks", []):
        print(json.dumps(r, ensure_ascii=False, indent=2))

"""
{
  "chunk_id": 465024973573395272,
  "distance": 0.7324684262275696,
  "entity": {
    "body": "\n原文第1句：鲁芝字世英，扶风郿人也，世有名德，为西州豪族。\n\n翻译：鲁芝，字世英，扶风郿地人，世代有名望德行， 是西州的豪门大族。\n\n原文第2句：父为郭氾所害，芝襁褓流离，年十七，乃移居雍，耽思坟籍。\n\n翻译：（鲁芝的）父亲被郭氾杀害，他很小的时候就颠沛流离，在十七岁那年，才移居到雍州，沉浸在古代典籍中。\n\n原文第3句：郡举上计吏，州辟别驾。\n\n翻译：郡举荐他为上计吏，州政聘他为别驾。\n\n原文第4句：魏车骑将军郭淮为雍州刺史，深敬重之。\n\n翻译：魏国车骑将军郭淮担任雍州刺史，十分尊敬器重他。\n\n原文第 5 句：举孝廉，除郎中，后拜骑都尉、参军事、行安南太守，迁尚书郎，曹真出\n\n督关右，又参大司马军事。\n\n翻译：（鲁芝）被推举为孝廉，被授予郎中一职，后来又被授予骑都尉、参军事、行安南太守，又升迁为尚书郎，曹真出京监督关右事务，（鲁芝） 又任大司马军事。\n\n原文第6句：真薨，宣帝代焉，乃引芝参骠骑军事，转天水太守。\n\n翻译：曹真薨了，宣帝代替他，于是推举鲁芝为参骠骑军事，转任天水太守。\n\n原文第 7 句：郡邻于蜀，数被侵掠，户口减削，寇盗充斥，芝倾心镇卫，更造城市，数年间旧境悉复。\n\n翻译：天水郡和蜀国相邻，多次遭受侵扰和抢掠，人口减少，盗贼横行，鲁芝全力镇压守卫，重新建造城市，几年之间就恢复旧貌。\n\n原文第8句：迁广平太守，天水夷夏慕德，老幼赴阙献书，乞留芝，魏明帝许焉。\n\n翻译：（鲁芝）迁为广平太守，天水郡各族人民仰慕（他的）德 行，老人小孩一起奔赴朝廷献上请愿书，乞求留下鲁芝，魏明帝答应了。\n\n原文第9句：曹爽辅政，引为司马，芝屡有谠言嘉谋，爽弗能纳。\n\n翻译：曹爽辅佐朝政，引荐他为司马，鲁芝多次献上好的见解与谋略，曹爽没有采纳（他的意见）。\n\n原文第10句：及宣帝起兵诛爽， 芝率余众犯门斩关，驰出赴爽，劝爽曰：“公居伊周之位，一旦以罪见黜，虽欲牵黄犬，复可得乎！若挟天子保许昌，杖大威以羽檄征四方兵，孰敢不从！舍此而去，欲就东市，岂不痛哉！”\n\n翻译：等到宣帝起兵诛杀曹爽，鲁芝率领部下打开城门斩杀守关的将领，疾驰而出奔赴曹爽之处，劝谏曹爽说：“您身居像伊尹和周公那样的官位，一旦因为获罪而被罢官，即使想过悠闲自在的日子，还能再次实现吗！如果挟持天子保卫许昌，依仗无上的威严用军文征讨天下，谁敢不听从呢！放弃这个决策而离去，想要去杀人的刑场，难道不令人痛心吗？！”\n\n原文第11句：爽懦惑不能用，遂委身受戮，芝坐爽下狱，当死，而口不讼直，志不苟免，宣帝嘉之，赦而不诛，俄而起为并州刺史。\n\n翻译：曹爽懦弱 糊涂不能采纳他的建议，最终束手就擒，接受杀戮，鲁芝也因为曹爽获罪而入狱，按律当死，然而（他）不为自己正直的行为辩解，心里不想 着随便赦免自己的罪行，宣帝赞许他，赦免他而不诛杀他，不久被起用为并州刺史。\n\n原文第12句：诸葛诞以寿春叛，魏帝出征，芝率荆州 文武以为先驱。\n\n翻译：诸葛诞凭借寿春反叛，魏帝出征讨伐，鲁芝率领荆州文武百官作为先锋。\n\n原文第13句：诞平，迁大尚书，掌刑 理，武帝践阼，转镇东将军，进爵为侯。\n\n翻译：诸葛诞之乱被平定，（鲁芝）升迁为大尚书，掌管刑法，武帝登基，转任镇东将军，晋封 侯爵。\n\n原文第14句：帝以芝清忠履正，素无居宅，使军兵为作屋五十间。\n\n翻译：皇帝认为鲁芝清廉忠心坚守正道，一向没有私宅，派 官兵为（他）建造五十间房子。\n\n原文第 15 句：芝以年及悬车，告老逊位，章表十余上，于是征为光禄大夫，位特进，给吏卒，门施行马 。\n\n翻译：鲁芝认为自己年龄到了七十岁，想告老退位，向皇帝递了十几次奏章，（皇上不答应），于是又被征召为光禄大夫，居高位，给 予官吏人马，允许在家门口放上木头架子，遮挡人马。\n\n原文第 16~17 句：羊祜为车骑将军，乃以位让芝，曰：“光禄大夫鲁芝洁身寡欲， 和而不同，服事华发，以礼终始，未蒙此选，臣更越之，何以塞天下之望！”上不从。其为人所重如是。\n\n翻译：羊祜担任车骑将军，于是（想）把这个官位让给鲁芝，说：“光禄大夫鲁芝洁身自好清心寡欲，与人和睦而不苟同，任职到老，始终坚守礼节，却没有成为这个官位的人选，我的官位更是超过了他，拿什么来满足天下人的期望！”皇上没有听从他的意见。鲁芝被人看重就像是这样。\n\n原文第18~19句：泰始九年 卒，年八十四。帝为举哀，谥曰贞，赐茔田百亩。\n\n翻译：鲁芝泰始九年去世，享年八十四岁。皇帝为他举行葬礼，谥号为贞，赏赐他墓田 百亩。\n",
    "title": "# 一、逐句精细翻译",
    "chunk_id": 465024973573395272
  }
}
{
  "chunk_id": 465024973573395271,
  "distance": 0.7116045355796814,
  "entity": {
    "body": "\n鲁芝字世英，扶风郿人也，世有名德，为西州豪族。父为郭氾所害，芝襁褓流离，年十七，乃移居雍，耽思坟籍。郡举上计吏，州辟别驾。魏车骑将军郭淮为雍州刺史，深敬重之。举孝廉，除郎中，后拜骑都尉、参军事、行安南太守，迁尚书郎，曹真出督关右，又参 大司马军事。真薨，宣帝代焉，乃引芝参骠骑军事，转天水太守。郡邻于蜀，数被侵掠，户口减削，寇盗充斥，芝倾心镇卫，更造城市，数年 间旧境悉复。迁广平太守，天水夷夏慕德，老幼赴阙献书，乞留芝，魏明帝许焉。曹爽辅政，引为司马，芝屡有谠言嘉谋，爽弗能纳。及宣帝 起兵诛爽，芝率余众犯门斩关，驰出赴爽，劝爽曰：“公居伊周之位，一旦以罪见黜，虽欲牵黄犬，复可得乎！若挟天子保许昌，杖大威以羽檄征四方兵，孰敢不从！舍此而去，欲就东市，岂不痛哉！”爽懦惑不能用遂委身受戮芝坐爽下狱当死而口不讼直志不苟免宣帝嘉之赦而不诛俄而起为并州刺史。诸葛诞以寿春叛，魏帝出征，芝率荆州文武以为先驱。诞平，迁大尚书，掌刑理，武帝践阼，转镇东将军，进爵为侯。帝以芝 清忠履正，素无居宅，使军兵为作屋五十间。芝以年及悬车，告老逊位，章表十余上，于是征为光禄大夫，位特进，给吏卒，门施行马。羊祜 为车骑将军，乃以位让芝，曰：“光禄大夫鲁芝洁身寡欲，和而不同，服事华发，以礼终始，未蒙此选，臣更越之，何以塞天下之望！”上不从 。其为人所重如是。泰始九年卒，年八十四。帝为举哀，谥曰贞，赐茔田百亩。\n\n（节选自《晋书·鲁芝传》）\n",
    "title": "# 2018 全国Ⅰ卷",
    "chunk_id": 465024973573395271
  }
}
{
  "chunk_id": 465024973573395303,
  "distance": 0.679722785949707,
  "entity": {
    "body": "\n1. 此之谓也：宾语前置，应为“谓此”，意为“说的就是这个（道理）”。“之”为助词，宾语前置的标志。\n\n2. 鲁人为人臣妾于诸侯：介词结构后置，应为“鲁人于诸侯为人臣妾”，意为“鲁国人在其他诸侯国做了他人的奴隶”。\n\n3.取其金于府：介词结构后置，应为“于府取其金”，意为“到官府拿取金钱”。\n\n4.无损于行：介词结构后置，应为“于行无损”，意为“对于德行没有损伤”。\n",
    "title": "# （三）重点句式",
    "chunk_id": 465024973573395303
  }
}
{
  "chunk_id": 465024973573395332,
  "distance": 0.38509076833724976,
  "entity": {
    "body": "\n1.\t 对下列句子中加点词语的解释，不正确的一项是（ ）。\n\nA. 发言必自称曰儒\n\n发言：发表意见\n\nB. 当时四方士大夫乐其无名教之拘\n\n拘：束缚、拘束\n\nC. 牧亦坐是废\n\n废：（被）罢免\n\nD. 实宽良有治行\n\n治行：政绩\n\n答案：A。\n\n解析：本题考查对文言实词的理解，注意课内外迁移，并结合上下文分析词义、词性。A项中的“发言”应为“开口说话”。文中原意指那些一开口说话就必定叫自己儒者的人。“发表意见”过于具体，相较原文有所偏颇。\n\n2.\t 下列各组句子中，加点词的意义和用法相同的一组是（ ）。\n\nA. 果足以充儒之名乎\n\n句读之不知\n\nB. 于其外则不光\n\n此其志不在小\n\nC. 卒于睢阳\n\n从径道亡，归璧于赵\n\nD. 将犬吠所怪\n\n为巡船所物色\n\n答案：B。\n\n解析：本题考查对文言虚词的理解，要求疏通句意，理解语法。A 项中的“之”分别为助词“的”和用于主谓间取消句子独立性的助词。B 项的中“其”均为代词“他的”。C 项中的“于”分别为介词“在”和介词“到”。D 项中第一个“所”与动词相连组成名词性 结构，第二个“所”与“为”共同组成被动标志。\n\n3.\t 下列对原文有关内容的概括与赏析，不正确的一项是（ ）。\n\nA. 作者认为，对真正的儒者而言，读书不应雕章琢句，作文不应只追求辞藻华丽，而应抱着学以致用的目的，匡正时弊，有益社会的进步。\n\nB. 颜太初考中进士后，担任过临晋主簿和应天府户曹。主簿是县令的属官，户曹是知府的属官。县令的上级是州牧。\n\nC. 颜太初宽厚正直，才识过人，效法嵇康、阮籍，诗文讥刺时事，遭到利益集团的嫉恨排挤，终身仕途不顺，郁郁不得志。\n\nD. 文章叙议结合。作者在记叙颜太初生平经历中，表达了欣赏的态度并寄寓深切同情；在评价颜太初诗文创作时，充分肯定了其作品的价值。\n\n答案：C。\n\n解析：本题考查理解文意、归纳与概括内容要点、辨析文章细节的能力。C 选项中称颜太初“效法嵇康、阮籍”，张冠李戴。由文中“青州牧有以荒淫放荡为事，慕嵇康、阮籍之为人……太初恶其为大乱风俗之本，作《东州逸党》诗以刺之”等句可知，效法嵇康、阮籍、不遵礼教的是青州牧，颜太初对这种现象表示批判。\n\n4.\t 用“/”给文中画波浪线的部分断句。\n\n世 人 见 太 初 官 职 不 能 动 人 又 其 文 多 指 讦 有 疵 病 者 所 恶 闻 虽得 其 文 不 甚 重 之 故 所 弃 失 居 多 余 止 得 其 两 卷\n\n答案：世人见太初官职不能动人 / 又其文多指讦/ 有疵病者所恶闻 / 虽得其文/ 不甚重之 /故所弃失居多/ 余止得其两卷\n\n解析：本题考查文言文断句能力，要求疏通文意，熟练掌握文言句式的特征，根据重点字词等信息 判断划分方法。首先，可以通过寻找主语为段落划分层次，可以找到“世人”“有疵病 者”“余”，确定三个层次。其次，可以结合文意，通过“又”“虽”“故”等连词或关联词语进行断句。\n\n5.\t 把文中画线的句子译成现代汉语。\n\n（1）既得其理，不徒诵之，以夸诳于人，必也蹈而行 之。\n\n答案见精翻。\n\n（2）前世之士身不显于时，而言立于后世者多矣。太初虽贱而夭，其文岂必不传？\n\n答案见精翻。\n",        
    "title": "# 三、试题解析",
    "chunk_id": 465024973573395332
  }
}
{
  "chunk_id": 465024973573395319,
  "distance": 0.38323158025741577,
  "entity": {
    "body": "\n1.因以为名也：把……当作。\n\n2.颜鲁公真卿为刺史：担任。\n\n3.靡不备焉：没有。\n\n4.飘然恍然：……的样子。\n\n5.得人而后发：连词，表承接。\n\n6.盖是境也：大概。\n\n7.盖是境也：代词，这个。\n\n8.是以余力济高情：因此。\n\n9.其吾友杨君乎：句 首语气词，表推测，“大概”。\n\n10.故名而字之：连词，表并列。\n",
    "title": "# （二）重点虚词",
    "chunk_id": 465024973573395319
  }
}
"""


