from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openai import OpenAI

from datetime import datetime, timedelta
# from config import POXA, WEEK_SUMMARY_CSS_SELECTOR, WEEK_CSS_SELECTOR

def get_summary(time=None):
    if time==None:
        date = datetime.today()
    else:
        today = datetime.today().strftime('%Y%m%d')
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages= [
                {"role": "system", "content": f"""
                    你是一個日期轉換工具，只會輸出八位數字（%Y%m%d），請不要輸出除了數字之外的東西
                    若未提供年份，請使用{today}對應的年份
                    若未提供年份與月份，請使用{today}對應的年份與月份
                    若未提供日期，請使用該月份的6號
                    """
                },
                {"role": "user", "content": time}
            ]
        )
        date = datetime.strptime(response.choices[0].message.content, '%Y%m%d')

        start_time = datetime(2023, 10, 2)
        if date < start_time:
            return None

        print(f"轉換後的日期: {response.choices[0].message.content}")

    # 拿到前一個週一的日期
    weekday = date.weekday()  # 週一為 0，週日為 6
    print(f"減 {weekday}")
    previous_monday = date - timedelta(days=weekday)
    previous_monday = previous_monday.strftime('%Y%m%d')
    print(f"上一個週一: {previous_monday}")

    return previous_monday

'''
def get_summary(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    # driver = webdriver.Chrome()
    driver.get(url)

    element = driver.find_element(By.CSS_SELECTOR, "#__next > div > div.relative.grid.justify-center > article > div.prose-a\:no-underline.prose-a\:text-cyan-800")
    html = element.get_attribute("innerHTML")
    html = html.replace('<a href="/', '<a target="_blank" href="https://info.poxa.io/')
    html = html.replace('src="/', 'src="https://info.poxa.io/')
    return html

def GET_SUMMARY_GPT(full_text):
    client = OpenAI()

    # 請 GPT 幫忙過濾掉無關的文字
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages= [
            {
            "role": "system",
            "content": f"請根據以下內容，幫我摘要出200字以內，並以階層式的列點形式呈現，需要使用 html 的標籤。內容如下：{full_text}"
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content

def get_web_with_week_summary():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(POXA)

    a_tag = driver.find_element(By.CSS_SELECTOR, WEEK_SUMMARY_CSS_SELECTOR)

    href = a_tag.get_attribute('href')
    driver.quit()

    return href


def check_token_send_to_gpt(text, max_tokens=3500):
    # 初始化 tiktoken 編碼器
    encoding = tiktoken.encoding_for_model("gpt-4o-mini")
    
    # tokens = encoding.encode(text)
    # return len(tokens)

    """將文本拆分成多個部分，每部分最多 max_tokens 個 tokens"""
    sentences = text.split('\n')  # 使用句子分割
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = len(encoding.encode(sentence))
        if current_tokens + sentence_tokens > max_tokens:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_tokens = 0
        current_chunk.append(sentence)
        current_tokens += sentence_tokens
    
    # 添加最後一個 chunk
    if current_chunk:
        chunks.append("。".join(current_chunk))
    
    return chunks


# 自動生成摘要
def auto_summary_test(plain_text, title):
    # print(f"標題:{title}")
    with open("functions/summary_example.txt", 'r', encoding='utf-8') as file:
        content = file.read()

    chunks = check_token_send_to_gpt(plain_text)

    client = OpenAI()

    # 請 GPT 幫忙過濾掉無關的文字

    messages = []
    messages.append({
        "role": "system",
        "content": f"""
        您是一個直到獲取所有資訊後，才摘要重點的助手，會按照期望的輸出格式給予回覆，請依照以下標題 {title} 進行摘要。
        其中「市場最新動態」還須包含四個子標題「調頻服務」、「E-dReg」、「即時備轉」、「補充備轉」，每個子標題需包含以下內容：
        「平均結清價格(required)」、「本週參與容量(required)」、「參與容量與上週的比較(required)」、「補充說明(optional)」。
        
        期望的輸出格式如下（它是過去的歷史資料，這只是給你參考輸出的格式，並非實際的數據，請不要參考其中的數據內容）:
        {content}。
        而實際的數據將分成{len(chunks)+1}次傳送，若資訊未全數傳送完畢，請回覆「請繼續傳送數據。」
        """
        })
    
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=messages,
        temperature=0
    )
    print(f"給定期望的輸出格式後: {response.choices[0].message.content}")

    # 逐段發送並處理回應
    part = 1
    for chunk in chunks:
        messages = []
        messages.append({
            "role": "user",
            "content": f"""
            實際的數據將分成{len(chunks)-part}次傳送。
            若資訊未全數傳送完畢，請回覆「請繼續傳送數據。」
            若傳送完畢，請開始摘要。

            實際的數據，第{part}部份如下：{chunk}。
            """
            # **注意**：請根據這些實際數據進行摘要，不要參考或使用上面期望輸出格式中的數據。
        })
        
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=messages,
            temperature=0
        )
        print(f"實際的數據(part{part}): {response.choices[0].message.content}")
        part += 1

    
    # gpt_responses.append(response.choices[0].message.content)

    # 合併所有回應
    # final_response = "\n".join(gpt_responses)
    # print(final_response)

    final_response = response.choices[0].message.content

    # html = response.choices[0].message.content
    with open("functions/auto_summary.html", 'w', encoding='utf-8') as file:
        file.write(final_response)
    

def auto_summary(plain_text, title):
    # print(f"標題:{title}")
    with open("functions/summary_example.txt", 'r', encoding='utf-8') as file:
        content = file.read()

    client = OpenAI()

    # 請 GPT 幫忙過濾掉無關的文字

    messages = []
    messages.append({
        "role": "system",
        "content": f"""
        您是一個直到獲取所有資訊後，才摘要重點的助手，會按照期望的輸出格式給予回覆，請依照以下標題 {title} 進行摘要。
        其中「台電最新公告」，若無可直接寫「本週台電沒有公告，POXA會持續追蹤最新公告。」。
        其中「市場最新動態」還須包含四個子標題「調頻服務」、「E-dReg」、「即時備轉」、「補充備轉」，每個子標題需包含以下內容：
        「平均結清價格(required)」、「平均結清價格較上週上升or下滑多少(required)」、「本週參與容量(required)」、「參與容量較上週上升or下滑多少(required)」、「補充說明(optional)」。
        
        期望的輸出格式如下（它是過去的歷史資料，這只是給你參考輸出的格式，並非實際的數據，請不要參考其中的數據內容）:
        {content}。

        而實際的數據如下:
        {plain_text}
        """
        })
    
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=messages,
        temperature=0
    )
    final_response = response.choices[0].message.content

    with open("functions/auto_summary.html", 'w', encoding='utf-8') as file:
        file.write(final_response)

def auto_get_text():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(POXA)

    a_tag = driver.find_element(By.CSS_SELECTOR, WEEK_SUMMARY_CSS_SELECTOR)
    href = a_tag.get_attribute('href')
    # driver.get(href)
    driver.get("https://poxa-info-client-git-report20240909-poxa.vercel.app/report/20240909")

    plain_text = "📈 市場最新動態"

    # button 要先拿，因為使用 XPATH，移除本週摘要的時候會影響到
    button_element = driver.find_element(By.XPATH, '//*[@id="__next"]/div/div[2]/article/div[5]/div[1]')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'button')))
    buttons = button_element.find_elements(By.TAG_NAME, 'button')
    paths = [
        #826
        # '#headlessui-tabs-panel-\:Rqbpl6\:',
        # '#headlessui-tabs-panel-\:R1abpl6\:',
        # '#headlessui-tabs-panel-\:R1qbpl6\:',
        # '#headlessui-tabs-panel-\:R2abpl6\:',
        # '#headlessui-tabs-panel-\:R2qbpl6\:',

        '#headlessui-tabs-panel-\:Rd59l6\:',
        '#headlessui-tabs-panel-\:Rl59l6\:',
        '#headlessui-tabs-panel-\:Rt59l6\:',
        '#headlessui-tabs-panel-\:R1559l6\:',
        '#headlessui-tabs-panel-\:R1d59l6\:'


        #902
        # # '//*[@id="headlessui-tabs-panel-:Rq8hl6:"]',
        # '#headlessui-tabs-panel-\:Rq8hl6\:',
        # # '//*[@id="headlessui-tabs-panel-:R1a8hl6:"]',
        # '#headlessui-tabs-panel-\:R1a8hl6\:',
        # # '//*[@id="headlessui-tabs-panel-:R1q8hl6:"]',
        # '#headlessui-tabs-panel-\:R1q8hl6\:',
        # # '//*[@id="headlessui-tabs-panel-:R2a8hl6:"]',
        # '#headlessui-tabs-panel-\:R2a8hl6\:',
        # # '//*[@id="headlessui-tabs-panel-:R2q8hl6:"]'
        # '#headlessui-tabs-panel-\:R2q8hl6\:'
    ]

    for i in range(0, 5):
        buttons[i].click()
        # test = driver.find_elements(By.CSS_SELECTOR, paths[i])
        
        panel_element = driver.find_element(By.CSS_SELECTOR, paths[i])
        p_elements = panel_element.find_elements(By.TAG_NAME, 'p')

        for p in p_elements:
            plain_text += f'\n{p.text}'

    # return

    # 移除本週摘要
    need_remove = driver.find_element(By.XPATH, '//*[@id="本週摘要"]')
    driver.execute_script("arguments[0].remove();", need_remove)
    need_remove = driver.find_element(By.XPATH, '//*[@id="__next"]/div/div[2]/article/div[3]')
    driver.execute_script("arguments[0].remove();", need_remove)

    element = driver.find_element(By.CSS_SELECTOR, "#__next > div > div.relative.grid.justify-center > article")
    elements = element.find_elements(By.CSS_SELECTOR, 'h2, p')

    # print(len(p_elements))

    for e in elements:
        plain_text += f'\n{e.text}'

    # 关闭 WebDriver
    driver.quit()

    with open("functions/plain_text.txt", 'w', encoding='utf-8') as file:
        file.write(plain_text)

    return plain_text

def auto_get_title():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(POXA)

    a_tag = driver.find_element(By.CSS_SELECTOR, WEEK_SUMMARY_CSS_SELECTOR)
    href = a_tag.get_attribute('href')
    # href="https://info.poxa.io/report/20240805"
    
    driver.get(href)
    h2_elements = driver.find_elements(By.TAG_NAME, 'h2')
    h2_elements = h2_elements[2:-1]
    h2_ids = [h2.get_attribute('id') for h2 in h2_elements]
    # print(h2_ids)

    head_elements = driver.find_elements(By.CSS_SELECTOR, 'h2, h3')
    head_elements = head_elements[2:-2]
    head = [h.get_attribute('id') for h in head_elements]
    # print(head)

    titles = {}
    for h in head:
        if h in h2_ids:
            temp = h
            titles[temp] = []
        else:
            titles[temp].append(h)

    # 输出所有的 id
    return h2_ids

print(auto_summary(auto_get_text(), auto_get_title()))
# text = auto_get_text()
# print(check_token_send_to_gpt(text))
'''