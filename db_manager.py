import pymongo
from pymongo.server_api import ServerApi

uri = "mongodb+srv://victoria91718:white0718@poxa.1j2eh.mongodb.net/?retryWrites=true&w=majority&appName=poxa"
client = pymongo.MongoClient(uri)

def db_addData(dbClient,dbName,data):
    mydb = client[dbClient] 
    mycol = mydb[dbName]
    if data:
        mycol.insert_many(data)
        print("Inserted new data into the database.")
    else:
        print("No new data to insert.")

def db_readData(dbClient, dbName, option, projection=None, find_one=False):
    mydb = client[dbClient]
    mycol = mydb[dbName]
    if find_one:
        data = mycol.find_one(option,projection)
    else:
        data = mycol.find(option,projection)
    return data

def db_createIndex(dbClient, dbName):
    mydb = client[dbClient]
    mycol = mydb[dbName]
    mycol.create_index([("content", "text"),
                        ("block.blockContent", "text"),
                        ("section.sectionContent", "text")])
    # mycol.drop_indexes() # 刪除所建立的索引
