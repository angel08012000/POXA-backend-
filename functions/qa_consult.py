from selenium import webdriver
from openai import OpenAI
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import json, re

def GET_COMMON_QA(url, question):
    client = OpenAI()
    main_url = url

    conversation = [
        {"role": "assistant", "content": "你是一個專業的關鍵字分析師，會根據這16類對問題進行分析，16類有:用電大戶、光儲合一、市場資訊、E-dReg、sReg、dReg、即時備轉、補充備轉、創新能源技術、電價方案、再生能源、台電說明會、規範解析和台電供需資訊。請根據問題分析該問題符合這16類中的哪幾類，並使用繁體中文回覆。除此之外，請回覆問題中涉及的時間關鍵字，例如：本週、今天。如果問題符合多個類別，請列出所有相關的類別關鍵字。"},
        {"role": "user", "content": "本週市場情況摘要？"}, 
        {"role": "assistant", "content": "市場資訊,本週"},
        {"role": "user", "content": "幫我說明目前sReg價金的計算方式？"},
        {"role": "assistant", "content": "sReg,規範解析,目前"},
        {"role": "user", "content": "光儲的參與資格是？"},
        {"role": "assistant", "content": "光儲合一,規範解析"}
    ]

    conversation.append({"role": "user", "content": question})

    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=conversation
    )

    new_answer = completion.choices[0].message.content
    print(new_answer)

    data_list = get_data_from_web(main_url, new_answer)
    summarys = []
    for data in data_list:
        subtitles = "\n".join([f"{key}: {value}" for key, value in data["subtitle"].items()])
        subcontents = "\n".join([f"{key}: {value}" for key, value in data["subcontent"].items()])
        sections = "\n".join([f"{key}: {', '.join(section)}" for key, section in data["section"].items()])
        
        data_text = f"""
        Title: {data['title']}
        Content: {data['content']}
        Labels: {', '.join(data['labels'].values())}
        Subtitles: {subtitles}
        Subcontents: {subcontents}
        Sections: {sections}
        """

        data_conversation = [
            {"role": "system", "content": "你是一個專業的文章摘要助手，會根據輸入的文本生成300字的摘要。請使用繁體中文回覆。"},
            {"role": "user", "content": f"請幫根據{question}從{data_text}總結內容"}
        ]

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=data_conversation
        )

        summary = completion.choices[0].message.content
        summarys.append(summary)

    if len(data_list) > 1:
        combined_summaries = "\n\n".join(summarys)
        final_conversation = [
            {"role": "system", "content": "你是一個專業的文章分析助手，會根據輸入的文本回答具體問題並生成摘要。請使用繁體中文回覆。"},
            {"role": "user", "content": f"請根據以下多篇文章的摘要回答問題:\n\n問題: {question}\n\n文章摘要:\n\n{combined_summaries}"}
        ]

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=final_conversation
        )

        final_summary = completion.choices[0].message.content
        print(final_summary)
        return final_summary
    else:
        print(summarys[0])
        return summarys[0]
    
def get_data_from_web(main_url, new_answer):
    driver = webdriver.Chrome()
    url  = main_url
    driver.get(url)

    categories = [
        "用電大戶", "光儲合一", "市場資訊", "E-dReg", "sReg", "dReg", "即時備轉", "補充備轉",
        "創新能源技術", "電價方案", "再生能源", "台電說明會", "規範解析", "台電供需資訊"
    ]
    target_tags = re.split('、|,',new_answer)
    limit_size = 5
    if target_tags[len(target_tags)-1] == "本週":
        limit_size = 1
    if limit_size != 1:
        tags_pos = [index for index, category in enumerate(categories) if category in target_tags]
        print(f"位置:{tags_pos}")
        tags = []

        tag_list = driver.find_element(By.CLASS_NAME,"flex.flex-wrap.gap-3.px-6")
        for i in range(len(tags_pos)):
            tag = tag_list.find_elements(By.XPATH, f".//a[contains(text(), '{categories[tags_pos[i]]}')]")
            # "E-dReg" & "dReg"  XPATH會抓符合字樣，需辨識
            if tag[0].text == categories[tags_pos[i]]:
                    tags.append(tag[0])
                    print(tag[0].text)
            else:
                tags.append(tag[1])
                print(tag[1].text)
        for t in tags:
            t.click()


    origin_url = driver.current_url
    data_list = []
    data_size = limit_size   # 要抓多少筆資料
    for target in range(data_size):
        links_list = driver.find_elements(By.TAG_NAME,"a")
        link = links_list[target+16].get_attribute('href') #first title start from 16
        title_list = driver.find_elements(By.CLASS_NAME,"text-2xl.font-bold")
        data_title = title_list[target].text
        content_list = driver.find_elements(By.CLASS_NAME,"text-gray-500")
        data_content = content_list[target].text
        label_list = driver.find_elements(By.CLASS_NAME,"mt-4.flex.gap-2")
        labels = label_list[target].find_elements(By.TAG_NAME,"span")
        # data_labels = [label.text for label in labels] 無序列
        data_labels = {index: label.text for index, label in enumerate(labels)}

        print(data_title)

        links_list[target+16].click()
        driver.get(link)

        # subtitle 2~7 & sub_content 0~5
        data_subtitle = []
        data_subContent = []
        data_section = [] 
        flag_k = 2
        # 0~5
        for flag in range(6):
            found_records = False
            while not found_records:
                subtitle = driver.find_elements(By.TAG_NAME, "p")
                records = subtitle[flag + flag_k].find_elements(By.TAG_NAME, "a")
                    
                if records:
                    try:
                        sub_content = subtitle[flag + flag_k].find_element(By.XPATH, 'following-sibling::ul')
                        found_records = True
                        for record in records:
                            if record.text == "下週預告❓":
                                break
                            data_subtitle.append(record.text)
                            data_subContent.append(sub_content.text)
                    except NoSuchElementException:
                        flag_k += 1 
                else:
                    flag_k += 1  # flag_k++ Rerun

        section_list = driver.find_elements(By.CLASS_NAME, "text-3xl.font-bold")
        for flag in range(1, len(section_list)):
            section_between_h2s = []
            section_part = []
            if section_list[flag].text == "下週預告❓":
                break
            sections = section_list[flag].find_elements(By.XPATH, 'following-sibling::*')
            for s in sections:
                if s == section_list[flag + 1]:
                    break
                section_between_h2s.append(s)
            for sbh in section_between_h2s:
                if sbh.tag_name == 'p':
                    section_part.append(sbh.text)
                elif sbh.tag_name == 'ul':
                    section_part.append(sbh.text)
                elif sbh.tag_name == 'ol':
                    section_part.append(sbh.text)
            data_section.append(section_part)
                    
        # Prepare data to save in JSON 
        data = {
            "title": data_title,
            "content": data_content,
            "labels": data_labels,
            "subtitle": {str(i): data_subtitle[i] for i in range(len(data_subtitle))},
            "subcontent": {str(i): data_subContent[i] for i in range(len(data_subtitle))},
            "section": {str(i): data_section[i] for i in range(len(data_section))}
        }
        
        data_list.append(data)
        driver.get(origin_url)
        
    print("爬完ㄌㄌㄌㄌ~")
    driver.close

    return data_list
