import json
import pymongo


connect_string = "mongodb+srv://victoria91718:white0718@poxa.1j2eh.mongodb.net/?retryWrites=true&w=majority&appName=poxa"
client = pymongo.MongoClient(connect_string)
mydb = client['Test']
my_collection = mydb['definitions']

all_term = list(my_collection.find())
term_list = [t['term'] for t in all_term]  
term_string = '、'.join(term_list)
#print(term_list)

def get_definition(term_to_find):
    data = my_collection.find_one({"term": term_to_find})
    if data != None:
        #print(data["definition"])
        return data["definition"]
    else:
        return "查無資料"