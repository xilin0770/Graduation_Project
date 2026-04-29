from pymongo import MongoClient
from pymongo.collection import Collection

# 1. 定义MongoDB的客户端
mongo_client = MongoClient("mongodb://admin:admin@192.168.200.130:27017")

# 2. 创建库
db = mongo_client["my_db"]

# 2. 创建表
collection = db["students"] # 这里的创建时延时惰性的，并不会立马创建，而是在你向里面插入数据时，才会创建看到


def insert_document(connection: Collection):
    result = collection.insert_one({
        "name": "张三",
        "age": 20,
        "major": "计算机科学"
    })

    print(result)


# insert_document(collection)

print(mongo_client.list_database_names())