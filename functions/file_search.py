import openai, os, re
from openai import OpenAI
# from functions.sentence_similarity import compute_similarity
# from db_manager import db_readData

openai.api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI()

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
    # user_message = "請根據以下問題選擇三個合適的檔案，分別以這些檔案提供三種回答。請勿替換專有名詞，如：E-dReg、sReg。用繁體中文回答。回答格式為\"檔案名：回答\"。問題如下：" + user_question
    messages = send_message(user_question,  my_thread, my_assistant)
    gpt_response = messages[0].content[0].text.value
    # print(gpt_response)

    # matches = gpt_response.strip().split("\n\n")
    # print(f"正規後的回答：\n{matches}")
    # final_res_list = compute_similarity(user_question, matches)
    # final_res = '\n\n'.join(final_res_list)

    # return final_res

    # print(gpt_response + "\n\n...正在選擇最適合答案...\n")
    # user_message = "請核對以上的回答是否符合檔案內容，若答案有誤請移除。"
    # messages = send_message(user_message,  my_thread, my_assistant)
    # return messages[0].content[0].text.value
    return gpt_response

def start_file_search(question):
    my_assistant = client.beta.assistants.retrieve("asst_IFk0TMIJ3RBDIP7W1Sk2dCVw")
    print(my_assistant.name)
    my_thread = client.beta.threads.create()
    
    responses = response_with_preprocess(question, my_thread, my_assistant)
    # responses = response_directly(question, my_thread, my_assistant)
    responses = re.sub(r'【\d+:\d+†source】', '', responses)

    print("gpt 答案：\n" + responses)
    return responses
