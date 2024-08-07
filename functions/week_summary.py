from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from openai import OpenAI

from config import POXA, WEEK_SUMMARY_CSS_SELECTOR, WEEK_CSS_SELECTOR

def GET_TEXT(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)

    # driver = webdriver.Chrome()
    driver.get(url)

    element = driver.find_element(By.CSS_SELECTOR, WEEK_CSS_SELECTOR)
    return element.text

def GET_SUMMARY_GPT(full_text):
    client = OpenAI()

    # 請 GPT 幫忙過濾掉無關的文字
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages= [
            {
            "role": "system",
            "content": f"請根據以下內容，幫我摘要出200字以內，並以列點的形式呈現。內容如下：{full_text}"
            }
        ]
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