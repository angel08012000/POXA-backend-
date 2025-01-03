import openai, os, re
from openai import OpenAI
from functions.sentence_similarity import compute_similarity
from db_manager import db_readData

openai.api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI()

# 同義詞
def synonym_analysis(user_input):
    synonyms = db_readData("WebInformation","synonyms",{})
    for synon in synonyms:
        if synon["term"] in user_input:
            user_input = user_input.replace(synon["term"], synon["vocabulary"])
    return user_input

#上傳檔案到 vector store
def upload_file(file_paths, my_vector_store):
    file_streams = [open(path, "rb") for path in file_paths]
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=my_vector_store.id,
        files=file_streams
    )
    '''
    file_to_upload = client.files.create(
        file=open(file_path, 'rb'),
        purpose='assistants'
    )
    '''
    return file_batch

def create_vector_store(vector_name):
    new_vector = client.beta.vector_stores.create(
        name=vector_name
    )
    return new_vector

def create_assistant(assistant_name, ins, my_vector_store):
    new_assistant = client.beta.assistants.create(
        name=assistant_name,
        instructions=ins,
        model="gpt-3.5-turbo",
        tools=[
            {"type": "file_search"}
        ],
        tool_resources={"file_search": {"vector_store_ids": [my_vector_store.id]}}
    )
    return new_assistant

def initiate_interaction(user_message, my_vector_store):
    new_thread = client.beta.threads.create()
    thread_message = client.beta.threads.messages.create(
        thread_id=new_thread.id,
        role="user",
        content=user_message,
        attachments=[
        { "tools": [{"type": "file_search"}] }
      ],
    )
    return new_thread

def trigger_assistant(my_thread, my_assistant):
    run = client.beta.threads.runs.create(
        thread_id=my_thread.id,
        assistant_id=my_assistant.id
    )

def send_message(user_message, my_thread, my_assistant):
    message = client.beta.threads.messages.create(
        thread_id=my_thread.id,
        role="user",
        content=user_message
    )
    run = client.beta.threads.runs.create_and_poll(
        thread_id=my_thread.id,
        assistant_id=my_assistant.id
    )
    # print(run)
    return list(client.beta.threads.messages.list(thread_id=my_thread.id, run_id=run.id))

def response_directly(user_question, my_thread, my_assistant):
    user_message = "請用繁體中文回答以下問題。回答格式為\"檔案名：回答\"。問題如下：" + user_question
    messages = send_message(user_message,  my_thread, my_assistant)
    return messages[0].content[0].text.value

def response_with_preprocess(user_question, my_thread, my_assistant):
    user_message = "請根據以下問題選擇三個合適的檔案，分別以這些檔案提供三種回答。請勿替換專有名詞，如：E-dReg、sReg。用繁體中文回答。回答格式為\"檔案名：回答\"。問題如下：" + user_question
    messages = send_message(user_message,  my_thread, my_assistant)
    gpt_response = messages[0].content[0].text.value
    print(gpt_response)

    # matches = gpt_response.strip().split("\n\n")
    # print(f"正規後的回答：\n{matches}")
    # final_res_list = compute_similarity(user_question, matches)
    # final_res = '\n\n'.join(final_res_list)

    # return final_res

    # print(gpt_response + "\n\n...正在選擇最適合答案...\n")
    # user_message = "請將上述和問題無關的回答移除，留下一到三個和問題相關的答案。"
    # messages = send_message(user_message,  my_thread, my_assistant)
    # return messages[0].content[0].text.value
    return gpt_response



def start_file_search(question):
    #建立 vector store
    #vector_store_name = "For POXA FAQ"
    #my_vector_store = create_vector_store(vector_store_name)
    vector_store_id = "vs_aNGnuTDnhWzZF7JjzGmfCJ1F"
    # my_vector_store = client.beta.vector_stores.retrieve(vector_store_id=vector_store_id)
    #print(my_vector_store.name)

    #上傳檔案
    #file_paths = ['D:\碩\POXA_chatbot\pdftest\market files\電力交易平台管理規範及作業程序.txt']
    #file_batch = upload_file(file_paths, my_vector_store)
    #print(file_batch.status)

    #取得已上傳的檔案
    #file = client.files.retrieve("file-rDms4HPiLIw8hNcZZTYcWRnb")
    #print(file.id)

    #建立 assistant
    # ins = "你是一個有禮貌且專業的知識型助理，請使用已提供的文件為基礎，並用繁體中文來回答問題，文件來源為台灣電力交易平台。"
    # assistant_name = "POXA engry assistant"
    # my_assistant = create_assistant(assistant_name, ins, my_vector_store)

    my_assistant = client.beta.assistants.retrieve("asst_IFk0TMIJ3RBDIP7W1Sk2dCVw")
    print(my_assistant.name)
    my_thread = client.beta.threads.create()

    question = synonym_analysis(question)
    
    responses = response_with_preprocess(question, my_thread, my_assistant)
    # responses = response_directly(question, my_thread, my_assistant)
    responses = re.sub(r'【\d+:\d+†source】', '', responses)
    print("最終答案：\n" + responses)
    return responses


#請問補充備轉容量是甚麼？
#請問甚麼是電能移轉複合動態調節備轉容量？
#請問調頻備轉容量測試如何進行？
#請問基準年的定義是甚麼？
#跟我介紹一下E-dReg的規範？
#成為合格交易者的資格是啥？請幫我整理申請流程。
