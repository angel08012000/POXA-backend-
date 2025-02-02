from db_manager import db_readData
from functions.file_search import start_file_search
from functions.gcloud_conversational_agent import start_conversational_agent

collections = [("價金", "price_calculation")]

def define_prompt(question):
    collection = ""
    prompt = ""
    prompt_to_send = ""
    for cole in collections:
        if cole[0] in question:
            collection = cole[1]
    if collection != "":
        data = db_readData("MarketRulesData", collection, None, find_one=False)
        for d in data:
            if d["tag"] in question:
                prompt = f"請將下列文字與已提供的檔案作為背景知識，內容如下：\n{d["content"]}\n\n請根據已有的資訊，針對問題提供三種回答，回答格式為\"檔案名：回答\"，並在每個答案中間換行。問題如下：\n{question}"
                break
    if prompt != "":
        prompt_to_send = prompt
    else:
        prompt_to_send =  f"請根據已提供的資料，針對以下問題提供三種回答，並註明你參考到的資料檔案名稱，回答格式為\"檔案名：回答\"，並在每個答案中間換行。問題如下：\n{question}"
    return prompt_to_send

def get_rules(question):
    prompt_to_send = define_prompt(question)
    print(f"prompt: \n{prompt_to_send}")
    
    # gpt
    response_with_gpt = start_file_search(prompt_to_send)
    print("=" * 25)
    # gemini
    response_with_gemini = start_conversational_agent(prompt_to_send)

    responses = f"gpt:\n{response_with_gpt}\n\ngemini:\n{response_with_gemini}"
    # print("最終答案：\n" + responses)
    return responses


# 請問補充備轉容量是甚麼？
# 請問甚麼是電能移轉複合動態調節備轉容量？
# 請問調頻備轉容量測試如何進行？
# 請問基準年的定義是甚麼？
# 跟我介紹一下E-dReg的規範？
# 成為合格交易者的資格是啥？請幫我整理申請流程。
# 請告訴我sReg價金的計算方式？