import time
from openai import OpenAI

client = OpenAI()
def team_related_QA(user_input):
    start_time = time.time()
    answer=""
    introduce="製作POXAGPT的主要成員有:梁晏慈、林芷穎、林珊銥，指導教授是馬尚彬老師。"
    prompt = f"請以下敘述回答下列問題：\n敘述：{introduce}\n問題：{user_input}\n回答："
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.4,
        messages=[
            {"role": "system", "content": f"你是一個專業的敘述分析師，請從敘述中分析出適合回答的內容。"}, 
            {"role": "user", "content": prompt}
        ]
    )
    answer = response.choices[0].message.content.strip()
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total_running_time : {elapsed_time:.2f} s")
    return answer