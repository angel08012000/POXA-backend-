import openai, os, re
from openai import OpenAI

openai.api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI()

# 上傳檔案到 vector store
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

def build_openai_assistant(vs_name, ins, assistant_name):
    # 建立 vector store
    vector_store_name = vs_name
    my_vector_store = create_vector_store(vector_store_name)
    vector_store_id = my_vector_store.id
    # vector_store_id = "vs_aNGnuTDnhWzZF7JjzGmfCJ1F"
    # my_vector_store = client.beta.vector_stores.retrieve(vector_store_id=vector_store_id)
    #print(my_vector_store.name)

    # 上傳檔案
    #file_paths = ['D:\碩\POXA_chatbot\pdftest\market files\電力交易平台管理規範及作業程序.txt']
    #file_batch = upload_file(file_paths, my_vector_store)
    #print(file_batch.status)

    # 取得已上傳的檔案
    #file = client.files.retrieve("file-rDms4HPiLIw8hNcZZTYcWRnb")
    #print(file.id)

    # 建立 assistant
    assistant_name = assistant_name
    my_assistant = create_assistant(assistant_name, ins, my_vector_store)

    return my_assistant