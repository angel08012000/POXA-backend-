ARTICLE_CSS_SELECTOR = "c-wiz.PO9Zff.Ccj79.kUVvS, c-wiz.XBspb" #c-wiz.XBspb
LINK_CSS_SELECTOR = "a.gPFEn, a.JtKRv"


LASTEST = "https://news.google.com/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNRFZxYUdjU0JYcG9MVlJYR2dKVVZ5Z0FQAQ?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant"
TOPICS = {
    "taiwan": "https://news.google.com/topics/CAAqJQgKIh9DQkFTRVFvSUwyMHZNRFptTXpJU0JYcG9MVlJYS0FBUAE?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant",
    "global": "https://news.google.com/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx1YlY4U0JYcG9MVlJYR2dKVVZ5Z0FQAQ?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant",
    "local": "https://news.google.com/topics/CAAqHAgKIhZDQklTQ2pvSWJHOWpZV3hmZGpJb0FBUAE/sections/CAQiWENCSVNQRG9JYkc5allXeGZkakpDRUd4dlkyRnNYM1l5WDNObFkzUnBiMjV5RGhJTUwyY3ZNWEUxWW14a2JITnFlZzRLREM5bkx6RnhOV0pzWkd4emFpZ0EqNQgAKjEICiIrQ0JJU0dqb0liRzlqWVd4ZmRqSjZEZ29NTDJjdk1YRTFZbXhrYkhOcUtBQVABUAE?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant",
    "business": "https://news.google.com/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx6TVdZU0JYcG9MVlJYR2dKVVZ5Z0FQAQ?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant",
    "science_technology": "https://news.google.com/topics/CAAqLAgKIiZDQkFTRmdvSkwyMHZNR1ptZHpWbUVnVjZhQzFVVnhvQ1ZGY29BQVAB?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant",
    "entertainment": "https://news.google.com/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNREpxYW5RU0JYcG9MVlJYR2dKVVZ5Z0FQAQ?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant",
    "pe": "https://news.google.com/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNRFp1ZEdvU0JYcG9MVlJYR2dKVVZ5Z0FQAQ?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant",
    "healthy": "https://news.google.com/topics/CAAqJQgKIh9DQkFTRVFvSUwyMHZNR3QwTlRFU0JYcG9MVlJYS0FBUAE?hl=zh-TW&gl=TW&ceid=TW%3Azh-Hant",
}

DB_LASTEST = "lastest"

##### 我是分隔線 #####

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json

from concurrent.futures import ThreadPoolExecutor

def GET_NEWS_FAST(url, top):
    info = GET_NEWS(url, top)
    with ThreadPoolExecutor(max_workers=len(info)) as executor:
        temp = [executor.submit(GET_TEXT_and_SUMMARY, i) for i in info]
        news = [t.result() for t in temp]
    return news

def GET_NEWS(url, top):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    # driver = webdriver.Chrome()
    driver.get(url)

    elements = driver.find_elements(By.CSS_SELECTOR, ARTICLE_CSS_SELECTOR)

    news = []
    topic = ""
    i = 0

    # 打印元素的文本
    for element in elements:
        if i>=top:
            break
        
        try:
            a_tag = element.find_element(By.CSS_SELECTOR, LINK_CSS_SELECTOR)

            topic = a_tag.text
            if len(news)>0 and topic == news[-1]["topic"]:
                continue

            link = a_tag.get_attribute("href").replace("./", "https://news.google.com/")
            news.append({
                "topic": topic,
                "url": link
            })

            # full_text = GET_TEXT(link)
            # summary = GET_SUMMARY_GPT(full_text, topic)

            # news.append({
            #     "topic": topic,
            #     "summary": summary,
            #     "url": link
            # })
            
            i+=1
        except NoSuchElementException:
            continue
    
    driver.quit()
    return news

def GET_TEXT_and_SUMMARY(info):
    try:
        full_text = GET_TEXT(info["url"])
        summary = GET_SUMMARY_GPT(full_text, info["topic"])
        info["summary"] = summary
    except:
        info["summary"] = ""
    return info

def GET_TEXT(url):
    # 拿到網頁裡的文字，過濾標籤
    # res = requests.get(url)
    # full_text =  BeautifulSoup(res.text,'html.parser').get_text()

    # options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    # driver = webdriver.Chrome(options=options)

    # 用 selenium 太慢了
    # driver = webdriver.Chrome()
    # driver.get(url)
    # wait = WebDriverWait(driver, 10)
    # wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    # page_source = driver.page_source

    # # 使用 BeautifulSoup 解析並獲取文本內容
    # soup = BeautifulSoup(page_source, 'html.parser')
    # full_text = soup.get_text()

    # # 關閉瀏覽器
    # driver.quit()

    # return full_text

    # 這個比較快
    response = requests.get(url)
    response.raise_for_status()  # 確保請求成功
    
    soup = BeautifulSoup(response.text, 'html.parser')
    full_text = soup.get_text()
    
    return full_text

def GET_SUMMARY_GPT(full_text, topic):
    client = OpenAI()

    # 請 GPT 幫忙過濾掉無關的文字
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages= [
            {
            "role": "system",
            "content": f"請根據以下內容，幫我摘要出200字以內，以「{topic}」為主題的文章。內容如下：{full_text}"
            }
        ]
    )

    return response.choices[0].message.content

def FORMAT_RESPONSE(key, value):
    with open('./response.json', 'r') as file:
        json_data = file.read()

    res = json.loads(json_data)
    res["ui_type"] = key
    res["data"][key] = value
    return res

def FORMAT_NEWS(news):
    res = []
    for i in range(len(news)):
        res.append(FORMAT_RESPONSE("link", {
            "url" : news[i]["url"],
            "content" : f"({i+1}) {news[i]['topic']}"
        }))
        
        if len(news[i]['summary'])>0:
            res.append(FORMAT_RESPONSE("text", {
                "tag" : "span",
                "content" : news[i]['summary']
            }))
        

        # res.append(FORMAT_RESPONSE("text", {
        #     "tag" : "span",
        #     "content" : f"({i+1}) {news[i]['topic']}\n{news[i]['summary']}"
        # }))
        # res.append(FORMAT_RESPONSE("link", {
        #     "url" : news[i]["url"],
        #     "content" : f"資料來源"
        # }))
    return res

def SHOW_MENU():
    res = []
    res.append(FORMAT_RESPONSE("text", {
        "tag" : "span",
        "content" : f"""您好～ 我是電力交易市場小助手，我能夠提供的功能類型包含:\n
        每週摘要、名詞解釋、QA 問答、規則查詢
        """
    }))
    
    res.append(FORMAT_RESPONSE("button", {
        "content": "摘要",
        "function": "get_week_summary"
    }))

    res.append(FORMAT_RESPONSE("button", {
        "content": "法規問答",
        "function": "get_market_rule"
    }))

    res.append(FORMAT_RESPONSE("button", {
        "content": "名詞解釋",
        "function": "get_define"
    }))

    res.append(FORMAT_RESPONSE("button", {
        "content": "其他問題",
        "function": "get_other_question"
    }))

    # res.append(FORMAT_RESPONSE("button", {
    #     "content": "QA 問答",
    #     "function": "get_qa_answer"
    # }))

    # res.append(FORMAT_RESPONSE("button", {
    #     "content": "電力交易市場規則",
    #     "function": "get_market_rule"
    # }))
    
    return res

def ADD_FILE_LINKS(response):
    links = dict()
    file_links = {
                '市場總覽':'https://drive.google.com/file/d/14YO3VEXliKn4TCM3e6MD8-4DvrNRvTcn/view?usp=sharing',
                '專業人員資格證明之取得程序':'https://drive.google.com/file/d/1NFzwPNrHgqcHzUqaWhNOzoSPaBdOboJ2/view?usp=sharing',
                '併網型儲能設備併網申請作業程序':'https://drive.google.com/file/d/1DvHfTtp0XqyExOnhGdTUipwRoY9GydNC/view?usp=sharing',
                '保證金收取、退還及參與費用收取程序':'https://drive.google.com/file/d/1cG2eAwoyA5g2agIET-xHqd5R11TZk7zA/view?usp=sharing',
                'SD-WAN VPN通道設定':'https://drive.google.com/file/d/1pa7FXjKXtfrNfCY-QuqG5ukEkv9zuKK3/view?usp=sharing',
                'E-dReg通訊API說明':'https://drive.google.com/file/d/1ouh-N6xVw6LruHjmlpmFHibCUnPWkBIM/view?usp=sharing',
                '通訊能力測試說明文件':'https://drive.google.com/file/d/1g48cpPG_6jl8kDoD58ManGnRShJYm9jG/view?usp=sharing',
                '輔助服務執行能力測試說明文件':'https://drive.google.com/file/d/1u8NYoAmEz_ka4yKMzfrXf0tIKYATPODx/view?usp=sharing',
                '日前輔助服務市場之交易表計設置位置錯誤態樣說明文件':'https://drive.google.com/file/d/10CdnOh4O-r_H2-sJuB9Ppy_4gs6aAKnh/view?usp=sharing',
                '交易資源變比器得採行措施之說明文件':'https://drive.google.com/file/d/1s44ARrc7gTese1LjjxeDcUjfDSFUnWwK/view?usp=sharing',
                '報價代碼重新測試說明文件':'https://drive.google.com/file/d/1YkelP1e7Vb9G8dQoGraaQQC8q3Qxn__y/view?usp=sharing',
                'E-dReg電能移轉排程之升降載率設定說明文件':'https://drive.google.com/file/d/1LQauvoylRz-REKfSU9BUrUTb0896uD1i/view?usp=sharing',
                'E-dReg遇59.50Hz作動模式說明文件':'https://drive.google.com/file/d/1i_tqjMZUEnxAwrl-UIBOGZkQAExR5bH-/view?usp=sharing',
                '日前輔助服務市場之價金結算付款程序':'https://drive.google.com/file/d/1MMEjD1s8o2Q5WimPXAstRBTs87b0Ndgy/view?usp=sharing',
                '日前輔助服務市場需求量估算方式說明文件':'https://drive.google.com/file/d/12mTk0FAK0L-9R-sOBufkMZ-Z5PpMSr7s/view?usp=sharing',
                '日前輔助服務市場月結算價金結算說明文件':'https://drive.google.com/file/d/1LdLMlg9hRKoHJNLl5OlxHvtyK03KjOMc/view?usp=sharing',
                '自用發電設備表計設置規定及結算方式說明文件':'https://drive.google.com/file/d/1Wwih8OAkzlWaSFAYkGQpIaWRKb9dRh17/view?usp=sharing',
                '需量反應交易表計設置規定及執行容量計算基準認定說明文件':'https://drive.google.com/file/d/16msI3qVO3v6l9PvRwpZh8cIAYdJGO9bN/view?usp=sharing',
                '備用容量市場參與及交易媒合程序':'https://drive.google.com/file/d/1rslEPlaQEESaZy7BsC8YVt1Iay4o9EZV/view?usp=sharing',
                '資訊公開項目':'https://drive.google.com/file/d/1ZMpLh3301P5Kb9KrfdoHQl9KMgURFt58/view?usp=sharing',
                '太陽光電發電設備結合儲能系統餘電合約':'https://drive.google.com/file/d/1pjYBRrwz1dgpjWWU-xxFCijzHUsY1jTu/view?usp=sharing',
                '備用供電容量管理辦法':'https://drive.google.com/file/d/1wGxoiAlRaW55U6rjkxLT4hYNi7G07Aa2/view?usp=sharing',
                '電力交易平台市場管理系統服務使用條款':'https://drive.google.com/file/d/1ih4tf53tW6emugDnoTgnER7cEAE3Waau/view?usp=sharing',
                '電力交易平台排除「政府採購法」函':'https://drive.google.com/file/d/17ZQ0mpajTJoptoo6NTqwOM3QbaNhw5bl/view?usp=sharing',
                '電力交易平台設置規則 逐條說明':'https://drive.google.com/file/d/1AVuFDzBRxUM0bICoW_c7NUbyOotF_3vm/view?usp=sharing',
                '電力交易平台管理規範及作業程序 - 113年7月經濟部核定函與台電公告文':'https://drive.google.com/file/d/19lwtBwg6mYRdpl1pe85zJFTnywD5Pxc6/view?usp=sharing',
                '電力交易平台管理規範及作業程序 - 全文':'https://drive.google.com/file/d/1GQ7vcm-BYMRX9Ge1XQvjCAW_IhD2aPqc/view?usp=sharing',
                '電力交易平台管理規範及作業程序 - 經濟部核定函與台電公告':'https://drive.google.com/file/d/1xohngxSdATSTh-5sKwUheEg0o05Emv-7/view?usp=sharing',
                '電力交易平台管理規範及作業程序 - 總說明與對照表(版次：TPC-MT-v02)':'https://drive.google.com/file/d/1mBAOFGPBBMR5kIjHVJYIb1PBkryvtM0-/view?usp=sharing',
                '電力交易平台管理規範及作業程序 - 總說明與對照表(版次：TPC-MT-v04)':'https://drive.google.com/file/d/1b3l_Xx9UVCjzmNIRfMJhBSWwojz_zUvG/view?usp=sharing',
                '電力交易平台管理規範及作業程序附件五表5-4及附件九表9-2_113經濟部核定函與台電公告':'https://drive.google.com/file/d/1iIFnAfpb4L9jNqmPDi27OXCNCCGYgLKs/view?usp=sharing',
                '電力交易平台管理規範及作業程序附件五表5-4及附件九表9-2_規定、修正總說明及對照表':'https://drive.google.com/file/d/1dsPM1wTypgS-cRhbOYcQsia9fhCvtD5d/view?usp=sharing',
                }
    
    for key, value in file_links.items():
        if key in response:
            links[key] = value
    return links

def CALL_FUNCTION_BY_NAME(function_name, function_args):
    global_symbols = globals()

    # 檢查 function 是否存在＆可用
    if function_name in global_symbols and callable(global_symbols[function_name]):
        # 呼叫
        function_to_call = global_symbols[function_name]
        return function_to_call(**function_args)
    else:
        # 丟出錯誤
        raise ValueError(f"Function '{function_name}' not found or not callable.")