from db_manager import db_readData

'''
all_term = list(my_collection.find())
term_list = [t['term'] for t in all_term]  
term_string = '、'.join(term_list)
print(term_string)
'''

def get_definition(term_to_find):
    data = db_readData("Test","definitions",{"term": term_to_find},find_one=True)
    print("get_definition")
    if data != None:
        #print(data["definition"])
        answer = data["definition"]
        return answer
    else:
        print("查無資料")
        return "查無資料"