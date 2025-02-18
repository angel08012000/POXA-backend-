from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI
import requests

from datetime import datetime, timedelta
import re
from db_manager import db_readData
from common import FORMAT_RESPONSE, SHOW_MENU
from config import POXA
# from config import POXA, WEEK_SUMMARY_CSS_SELECTOR, WEEK_CSS_SELECTOR

# gemini
from langchain_google_vertexai import ChatVertexAI
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './poxa-443807-5fec254a4a5f.json'


def call_function_by_name(function_name, function_args):
    global_symbols = globals()

    # 檢查 function 是否存在＆可用
    if function_name in global_symbols and callable(global_symbols[function_name]):
        # 呼叫
        function_to_call = global_symbols[function_name]
        return function_to_call(**function_args)
    else:
        # 丟出錯誤
        raise ValueError(f"Function '{function_name}' not found or not callable.")

# def extract_time(user):
#     llm = ChatVertexAI(
#         model="gemini-1.5-pro",
#         temperature=0,
#         max_tokens=None,
#         max_retries=6,
#         stop=None,
#         # other params...
#     )

#     messages = [
#         (
#             "system",
#             f"""
#             你是一個判斷工具，只能從使用者輸入中提取與時間相關的描述，並輸出原文中的相應部分。
#             非使用者輸入，就不能出現在輸出。
#             切勿新增任何字，也切勿進行提問或要求更多上下文。
#             如果輸入中沒有與時間相關的內容，直接輸出空白。
#             """,
#         ),
#         ("human", user),
#     ]
#     ai_msg = llm.invoke(messages)
#     result = ai_msg.content
#     print(f"提取時間: {result}")

#     return result

def get_summary(time):
    # time = extract_time(user)

    llm = ChatVertexAI(
        model="gemini-1.5-pro",
        temperature=0,
        max_tokens=None,
        max_retries=6,
        stop=None,
        # other params...
    )

    messages = [
        (
            "system",
            f"""
            你是一個判斷工具，只會輸出 "1" 跟 "2"
            若使用者所描述的時間長度大於 7 天，輸出 "1"
            否則，輸出 "2"
            """,
        ),
        ("human", time),
    ]
    ai_msg = llm.invoke(messages)
    result = ai_msg.content

    print(f"判斷結果: {result}")

    res = list()

    if result.strip()=="1": # 整理多篇的摘要
        today = datetime.today().strftime('%Y%m%d')
        print("多篇摘要總結")
        messages = [
            (
                "system",
                f"""
                你是一個日期判斷工具，只會輸出開始日期(%Y%m%d)、結尾日期(%Y%m%d)
                中間以 "," 來分隔，不要加任何的空白
                今天日期為 {today}

                請根據使用者的描述來判斷開始、結尾日期
                """,
            ),
            ("human", time),
        ]
        ai_msg = llm.invoke(messages)
        result = ai_msg.content

        # result = response.choices[0].message.content
        print(f"開始、結尾日期分別是: {result}")

        start_date_str, end_date_str = result.split(",")

        # 轉換為日期物件
        start_date = datetime.strptime(start_date_str, "%Y%m%d")
        end_date = datetime.strptime(end_date_str, "%Y%m%d")

        # 計算日期差距
        date_difference = (end_date - start_date).days

        # 判斷是否超過 31 天
        if date_difference > 31:
            return [FORMAT_RESPONSE("text", {
                "tag": "span",
                "content": "時間範圍過長，請給定 1 個月內的範圍！"
            })]

        else:
            mondays = get_all_monday(start_date, end_date)

            year = start_date.strftime("%Y")
            month = start_date.strftime("%m").lstrip("0")
            day = start_date.strftime("%d").lstrip("0")

            query = {"$or": [
                {"title": {"$regex": rf"{year}/{month}/", "$options": "i"}},
                {"title": {"$regex": rf"{year} {month}/", "$options": "i"}}
            ]}
            articles = db_readData("WebInformation", "article", query, find_one=False)
            # print(f"as:\n{articles}")
            
            all_summary = ""
            for article in articles:
                # print(f"title: {article["title"]}")
                all_summary += get_summary_block(article)

            if all_summary == "":
                return [FORMAT_RESPONSE("text", {
                    "tag": "span",
                    "content": f"該範圍（{start_date_str}～{end_date_str}） 無摘要"
                })]
            # with open("./test_summary", "w", encoding="utf-8") as file:
            #     file.write(all_summary)

            messages = [
                (
                    "system",
                    f"""
                    你是一個重點整理工具，請幫忙摘要以下重點
                    """,
                ),
                ("human", all_summary),
            ]
            ai_msg = llm.invoke(messages)
            result = ai_msg.content

            res.extend([
                FORMAT_RESPONSE("text", {
                    "tag": "span",
                    "content": f"{start_date_str}～{end_date_str} 的摘要重點彙整如下:"
                }),
                FORMAT_RESPONSE("text", {
                    "tag": "span",
                    "content": result
                })
            ])

            for m in mondays:
                date = m.strftime("%Y%m%d")
                res.append(FORMAT_RESPONSE("link", {
                    "url": f"{POXA}/report/{date}",
                    "content": f"{date}（點我查看）"
                }))
            

    else: # 單篇摘要
        print("單篇摘要")
        previous_monday = get_summary_one_week(time)
        if previous_monday == None:
            return [FORMAT_RESPONSE("text", {
                "tag": "span",
                "content": "時間過早/還沒到（第一篇摘要是 2023/10/2 發布）"
            })]
        
        # 單篇摘要
        res.append(
            FORMAT_RESPONSE("text", {
                "tag": "span",
                "content": "週摘要如下（註：每週摘要由週一發佈）"
            })
        )
            
        # 查詢最新可用的連結
        while True:
            # 將日期合併成連結
            response = requests.get(f"{POXA}/report/{previous_monday}")
            
            if response.status_code == 200:
                res.append(FORMAT_RESPONSE("link", {
                    "url": f"{POXA}/report/{previous_monday}",
                    "content": f"{previous_monday}（點我查看）"
                }))
                break
            # 若未找到摘要，退回一週
            date = datetime.strptime(previous_monday, "%Y%m%d")
            date -= timedelta(days=7)
            print("倒退一週!")
            previous_monday = date.strftime("%Y%m%d")

    return res
        
        

# ver. GPT
def get_summary_one_week(time):
    if time==None:
        date = datetime.today()
    else:
        today = datetime.today().strftime('%Y%m%d')

        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages= [
                {"role": "system", "content": f"""
                    你是一個日期轉換工具，只會輸出八位數字（%Y%m%d），請不要輸出除了數字之外的內容。

                    %d:
                    若有明確的數字 day，則 %d = day
                    若指定了第n週，則先將 n 轉換為數字，而 %d 應該是該月份的第 7*n 天，即 n*7。
                    若未指定，請默認 %d = 7

                    %m:
                    若有明確的數字 month，則 %m = month
                    若未指定，請默認使用 {today} 中的 %m

                    %Y:
                    若有明確的數字 year，則 %Y = year
                    若未指定，請默認使用 {today} 中的 %Y

                    若出現「本週」，則輸出 {today}。
                    """
                },
                {"role": "user", "content": time}
            ]
        )

        print(f"判斷出的日期: {response.choices[0].message.content}")
        date = datetime.strptime(response.choices[0].message.content, '%Y%m%d')

        start_time = datetime(2023, 10, 2)
        if date < start_time:
            return None
        if date > datetime.today():
            return None

        print(f"轉換後的日期: {response.choices[0].message.content}")

    # 拿到前一個週一的日期
    weekday = date.weekday()  # 週一為 0，週日為 6
    print(f"減 {weekday}")
    previous_monday = date - timedelta(days=weekday)
    previous_monday = previous_monday.strftime('%Y%m%d')
    print(f"上一個週一: {previous_monday}")

    return previous_monday


# ver. Gemini
# def get_summary_one_week(time):

#     if time==None:
#         date = datetime.today()
#     else:
#         today = datetime.today().strftime('%Y%m%d')

#         llm = ChatVertexAI(
#             model="gemini-1.5-pro",
#             temperature=0,
#             max_tokens=None,
#             max_retries=6,
#             stop=None,
#             # other params...
#         )

#         messages = [
#             (
#                 "system",
#                 f"""
#                 你是一個日期轉換工具，只會輸出八位數字（%Y%m%d），請不要輸出除了數字之外的內容。

#                 %d:
#                 若有明確的數字 day，則 %d = day
#                 若指定了「第n週」，則先將 n 轉換為數字，而 %d 應該是該月份的第 7*n 天，即 n*7。
#                 若未指定，請默認 %d = 7

#                 %m:
#                 若有明確的數字 month，則 %m = month
#                 若未指定，請默認使用 {today} 中的 %m

#                 %Y:
#                 若有明確的數字 year，則 %Y = year
#                 若未指定，請默認使用 {today} 中的 %Y

#                 若出現「本週」，則輸出 {today}。
#                 """,
#             ),
#             ("human", time),
#         ]
#         ai_msg = llm.invoke(messages)
#         result = ai_msg.content

#         print(f"判斷出的日期: {result}")
#         date = datetime.strptime(result, '%Y%m%d')

#         start_time = datetime(2023, 10, 2)
#         if date < start_time:
#             return None
#         if date > datetime.today():
#             return None

#     # 拿到前一個週一的日期
#     weekday = date.weekday()  # 週一為 0，週日為 6
#     print(f"減 {weekday}")
#     previous_monday = date - timedelta(days=weekday)
#     previous_monday = previous_monday.strftime('%Y%m%d')
#     print(f"上一個週一: {previous_monday}")

#     return previous_monday

def get_all_monday(start_date, end_date):
    mondays = []
    current_date = start_date

    # 將 current_date 調整到最近的週一
    while current_date.weekday() != 0:  # 0 是週一
        current_date += timedelta(days=1)

    # 循環添加每個週一到列表，直到超過 end_date
    while current_date <= end_date:
        mondays.append(current_date)
        current_date += timedelta(days=7)  # 每次加 7 天到下一個週一

    return mondays

def get_summary_block(article):
    summary = ""
    for i, bk in article["block"].items():
        # print(bk)
        summary = summary + bk["blockContent"]
    return summary
    # try:
    #     summary = ""
    #     article = db_readData("WebInformation","article",{"title": title},find_one=True)
    #     for bk in article["block"]:
    #         print(bk)
    #         summary = summary + bk["blockContent"]
    #     return summary
    
    # except Exception as e:
    #     print(f"找不到摘要區塊{e}")
    #     return ""

# def get_summary_block(date):
#     options = webdriver.ChromeOptions()
#     options.add_argument("--headless")  # 啟用無頭模式
#     options.add_argument("--no-sandbox")  # 避免沙盒問題（推薦在 Linux 系統上加上這個參數）
#     options.add_argument("--disable-dev-shm-usage")  # 避免資源限制錯誤

#     # 自動下載並使用對應版本的 ChromeDriver
#     service = Service(ChromeDriverManager().install())
#     driver = webdriver.Chrome(service=service, options=options)

#     driver.get(f"{POXA}/report/{date}")

#     try:
#         summary = driver.find_element(By.XPATH, '//*[@id="__next"]/div/div[2]/article/div[3]')
#         return summary.text.strip() # 提取文字內容
    
#     except Exception as e:
#         print(f"找不到摘要區塊")
#         return ""
