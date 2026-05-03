# import torch

# print("PyTorch 版本:", torch.__version__)
# print("PyTorch 使用的CUDA版本:", torch.version.cuda)
# print("CUDA是否可用:", torch.cuda.is_available())

# if torch.cuda.is_available():
#     print("GPU 设备名称:", torch.cuda.get_device_name(0))


# # 如果CUDA可用，返回 "cuda:0"，否则返回 "cpu"
# device = f"cuda:{torch.cuda.current_device()}" if torch.cuda.is_available() else "cpu"
# print(device)  # 输出: cuda:0 或 cpu

# import os
# import dotenv
# from pymilvus import MilvusClient

# dotenv.load_dotenv()

# milvus_uri = os.getenv('MILVUS_URL', 'http://192.168.200.130:19530')

# # 3. 定义MilVusClient对象
# milvus_client = MilvusClient(
#     uri=milvus_uri
# )


# # 删除名为 "test_collection" 的集合
# milvus_client.drop_collection(collection_name="kb_item_names")
# print("集合已删除")

# import json

# file_path = r"D:\pycharm\project\shopkeeper_brain\knowledge\processor\import_process\import_temp_dir\pdf文档\md文档\万用表RS-12的使用\hybrid_auto\chunks_vector.json"
# with open(file_path, "r", encoding="utf-8") as f:
#     content = json.load(f)

# print(len(content["chunks"]))

# a = {"6":0.00867462158203125,"1173":0.133544921875,"3895":0.179931640625,"5873":0.243896484375,"9955":0.26416015625,"18912":0.218017578125,"28406":0.1630859375}

# print(len(a))

# from agents.mcp import MCPServerSse
# import asyncio
# from agents import Agent, Runner
# import os
# import dotenv
# dotenv.load_dotenv()
# api_key = os.getenv('OPENAI_API_KEY')

# async def test_mcp():
#     # ... 您的异步代码
#     mcp_client =  MCPServerSse(
#         name="通用搜索",
#         params={
#             "url": "https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/sse",  # 服务端的端点
#             "headers": {"Authorization":api_key}   # 认证权限 api_key
#         },
#             cache_tools_list=True,  # mcp服务端工具列表的工具做缓存
#     )
#     # 2. 建立mcp连接
#     await mcp_client.connect()
#     execute_tool_result = await mcp_client.call_tool(tool_name="bailian_web_search",
#                                                     arguments={"query": "今天周几", "count": 2})

#     return execute_tool_result

# try:
#     loop = asyncio.get_event_loop()
#     if loop.is_running():
#         # 如果事件循环正在运行，我们处于异步环境
#         print("请在异步环境中调用此函数")
#     else:
#         print(1)
#         mcp_result = loop.run_until_complete(test_mcp())
#         print(mcp_result)
        
# except RuntimeError:
# # 没有事件循环时创建一个新的
#     mcp_result = asyncio.run(test_mcp())
#     print(mcp_result)


# from openai import OpenAI

# client = OpenAI(
#     api_key="sk-gaqbbjkqarfebmcelwsdglzehyljsuxdnopwxnzpzbphfghy",
#     base_url="https://api.siliconflow.cn/v1"
# )

# response = client.chat.completions.create(
#     model="Pro/deepseek-ai/DeepSeek-V3.2",
#     messages=[
#         {"role": "system", "content": "你是一个有用的助手"},
#         {"role": "user", "content": "你好，请介绍一下你自己"}
#     ]
# )
# print(response.choices[0].message.content)

# response = client.chat.completions.create(
#                 model="Qwen/Qwen3.5-27B",
#                 messages=[
#                     {
#                         "role": "user",
#                         "content": [
#                             {
#                                 "type": "text",
#                                 "text": f"""任务: 为Markdown文档中的图片生成一个简短的中文标题。
#                                 背景信息：
#                                     1. 所属文档标题："高中数学知识点归纳"
#                                     2. 图片上下文：'# 4、演绎推理\n论，这种推理称为演绎推理。\n\n简言之，演绎推理是由一般到特殊的推理。演绎推理的一般模式——“三段论”，包括\n\n(1)大前提 ---- 已知的一般原理;  \n(2)小前提 ----所研究的特殊情况；  \n(3)结论 ----据一般原理，对特殊情况做出的判断.\n\n用集合的观点来理解：若集合 M 中的所有元素都具有性质 P, S 是 M 的一个子集, 那么 S 中所有元素\n\n也都具有性质 P.\n从推理所得的结论来看，合情推理的结论不一定正确，有待进一步证明；演绎推理在前提和推理形式都正确的前提下，得到的结论一定正确。'
#                                     请结合图片视觉内容和上述上下文信息，用中文简要总结这张图片的内容，
#                                     生成一个精准的中文标题（不要包含"图片"二字）。""",  
#                             },
#                             {
#                                 "type": "image_url",
#                                 "image_url": {
#                                     "url": f"data:image/jpeg;base64,'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K0+ynjhJ4lU5GK09M+F91eFZ9WvjKepR1oAbqnxIvLqTytLhkfPdDWfDpfifxFKPtDSwxt/fFem6X4P0jS1XyrSMOP4gK3URUUKowBQB51pvwwhjZZL2RJvUYrrLLwrpViB5VqoI7ituigBkcKRLhBgU+iigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAqOWCOZdrrkVJRQBg3vhHSL0HzLVSx7muR1L4XoWMtjMkJ9AK9MooA8Tks/FHhuXMJmnQf3BWrpvxKmt2EepROhHB3mvVXjSRdrjIrn9U8F6NqaN5lpHvP8AERQBJpXivTtUQGOdAT2zW4kiSDKsCPavJdS+G9/prNPpN6ygciNBWbB4y8ReHZBDqFhOYwcGRjxigD26iuR0Hx5pWs7Y0uY/Oxyuea6tJUkXKnIoAfRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFZmr67Y6LbNNdzBABQBpEhQSegrkvEvj7SdBiZXuEM/QIT1NcJrPjbVvFErWmiRHyiceahwa0/DXw1Lst1rEr3Mh52yjOKAMKbWvFnjWUJZWs1rasf9dGc8V1Ph74V29q4udWuDfyntMvT8q76x0220+ERW8KxqOyirlAFWz02zsIxHa26RKOy1aoooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKo32kWOooVuraOUH+9V6igDy7xB8Kkkle70a7axlAyFhXrXOWfibxV4KkWDVLKW4tg2DcSHtXumKoajpNpqcJjuYUkB/vCgDH8P+N9I16JRBcoZSOUHaunByMivIfEPw2ntLhr7Rp5IWBz5cfAqHQvH+paJcrYa3DsGdvmMcmgD2SiqOm6ta6pbrNbSB1IzV6gAooooAKKKKACiiigAooooAKKKKACkZgoyTgU2WVIULuQAK8y8Y+PSjmw0755m44FAG34v8e2mg2zRwMJLo/dTFcDp2i614zuvtN+0kcBbIUNxitnwx4En1GddS1YsxJyFJyOa9RtLKGziWOJFUAY4GKAMnQ/C1lo8CrHEu7HJ21vBQowBilooAKKKKACiiig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' "
#                                 }
#                             }
#                         ]
#                     }
#                 ],
#             )
# summary = response.choices[0].message.content.strip()

import json
import asyncio
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams

async def test_mcp():
# 1. 创建mcp客户端[1. host 2. http 2.1 streamable(主要建议使用)http 2.2sse http 3. stdio sse]
    mcp_client = MCPServerStreamableHttp(
        name = "通用搜索",
        cache_tools_list = True, # mcp服务端工具列表的工具做缓存
        params = MCPServerStreamableHttpParams({
            "url":"https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/mcp", # 服务端的端点
            "headers":{"Authorization": 'sk-81d21f0e2a7a4f899754677510b2e82e'} # 认证权限 api_key
        },
        timeout= 10, # 超时时间 10秒
        sse_read_timeout= 60, # sse的超时时间 60秒
        )
    )
    await mcp_client.connect()
    # 2. 执行工具
    tool_result = await mcp_client.call_tool(tool_name = "bailian_web_search", arguments = {
        "query": '今天周几？',
        "count": 3
    })

    return tool_result


try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # 如果事件循环正在运行，我们处于异步环境
        print("请在异步环境中调用此函数")
    else:
        mcp_result = loop.run_until_complete(test_mcp())
        print(mcp_result)
        
except RuntimeError:
# 没有事件循环时创建一个新的
    mcp_result = asyncio.run(test_mcp())
    print(mcp_result)    
