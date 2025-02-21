import re, opencc, time, jieba
from pymongo.server_api import ServerApi
from openai import OpenAI
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
from db_manager import db_readData

client = OpenAI()
model = SentenceTransformer('all-MiniLM-L6-v2')
converter = opencc.OpenCC('s2tw')

def extract_date_from_title(title):
    # 日期格式為 "YYYY MM/DD"
    match = re.search(r'(\d{4}) (\d{1,2})/(\d{1,2})', title)
    if match:
        year, month, day = map(int, match.groups())
        return datetime(year, month, day)
    return None

def search_latest_article():
    current_date = datetime.now()
    all_articles = list(db_readData("WebInformation","article",{}, {"title": 1})) 
    closest_article = None
    closest_date_diff = float('inf') 
    article_title = ""

    for article in all_articles:
        title = article['title']
        article_date = extract_date_from_title(title)
        if article_date:
            date_diff = abs((current_date - article_date).days) 
            if date_diff < closest_date_diff:
                closest_date_diff = date_diff
                closest_article = article
                article_title =title

    full_article = db_readData("WebInformation","article",{"_id": closest_article["_id"]},find_one=True)
    return full_article, article_title

def extract_keywords(question):
    global gpt_calls
    gpt_calls+=1
    nouns = list(db_readData("WebInformation","definitions",{}))
    terms = [noun['term'] for noun in nouns]  
    terms_string = '、'.join(terms) 
 
    prompt = f"請提取以下問題中的關鍵詞，使用逗號分隔：\n問題：{question}\n\n關鍵詞："
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.2,
        messages=[
            {"role": "system", "content": f"你是一個專業的問題解答助手，請從問題中提取出關鍵詞，遇到以下關鍵字請勿拆解它:{terms_string}"}, #:光儲合一、光合作用、調頻轉備。
            {"role": "user", "content": prompt}
        ]
    )
    keywords = response.choices[0].message.content.strip()
    keywords_traditional = converter.convert(keywords)
    keywords_cleaned = re.sub(r'\s*[,\n]+\s*', ',', keywords_traditional) 
    keywords_neat = [keyword.strip() for keyword in keywords_cleaned.split(',') if keyword.strip()]
    keyword_list = {str(index): keyword for index, keyword in enumerate(keywords_neat)}
    return keyword_list

def classify_question_time(question):
    global gpt_calls
    gpt_calls += 1
    prompt = f"請判斷以下問題是否有提及到目前、當前、最近或最新等相似的時間點字眼：\n問題：{question}\n\n請回答是或否就好，無須回答其他額外資訊："
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.1,
        messages=[
            {"role": "system", "content": "你是一個專業的問題分類助手，請判斷問題是否有明確提及到當前或最新等相似的時間點字眼。"},
            {"role": "user", "content": prompt}
        ]
    )
    answer = response.choices[0].message.content.strip()
    if "是" in answer :
        return True
    else:
        return False

def classify_question(question):
    global gpt_calls
    gpt_calls+=1
    prompt = f"請將以下問題分類：\n問題：{question}\n\n分類："
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.3,
        messages=[
            {"role": "system", "content": "你是一個專業的問題解答助手，請將問題分類成數據型問題和敘述型問題，如果是敘述型問題的話，請再細分為事實性問題、意見性問題或推理性問題。"},
            {"role": "user", "content": prompt}
        ]
    )
    classification = response.choices[0].message.content.strip()
    classification_traditional = converter.convert(classification)
    return classification_traditional

def search_articles(question):
    global gpt_calls
    keywords = extract_keywords(question)
    print("Keywords:", keywords)
    query = {"$text": {"$search": " ".join(keywords)}}
    results = db_readData("WebInformation","article",query)
    result_list = []
    
    if results == []:
        print("Empty")
        return result_list  
       
    for result in results:
        combined_content = ""
        # combined_content += f"段落標題: {result['title']}\n"
        # combined_content += f"段落簡介: {result['content']}\n"
        # for i, block in result['block'].items():
        #     combined_content += f"段落內容: {block['blockContent']}\n"
        for i, section in result['section'].items():
            combined_content += f"部分內容: {section['sectionContent']}\n"
        combined_content += "\n"

        gpt_calls += 1
        prompt = f"問題: {question}\n\n根據以下內容生成最符合的回答，回答請在500字左右:\n{combined_content}\n\n回答:"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0.8,
            messages=[
                {"role": "system", "content": "你是一個專業的問題解答助手，請根據資料直接回答問題，不要提供額外的解釋或背景資訊。"},
                {"role": "user", "content": prompt}
            ]
        )
        result_list.append({"title": result["title"], "response": response.choices[0].message.content.strip()})
    return result_list

def generate_answer(question, article, classification):
    global gpt_calls
    gpt_calls+=1
    ans_type = ""
    if "事實性問題" in classification:
        ans_type = "簡明"
    elif "意見性問題" in classification:
        ans_type = "詳細"
    elif "推理性問題" in classification:
        ans_type = "綜合"

    question, synonym_term =synonym_analysis(question)
    if synonym_term!=[]:
        print("get_synonym\n")
        print("test:",question, " ",synonym_term)
        content_str = extract_content(article) 
        filtered_content = "\n".join([line for line in content_str.splitlines() if synonym_term in line])
        prompt = f"問題: {question}\n根據以下內容中有關{synonym_term}的資訊回答問題:\n{filtered_content}\n\n回答詳細問題:"
    else:
        prompt = f"問題: {question}\n\n根據以下文章內容生成{ans_type}的回答:\n{article}\n\n回答:"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.8,
        messages=[
            {"role": "system", "content": "你是一個專業的問題解答助手，請根據資料直接回答問題，不要提供額外的解釋或背景資訊。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def text_embedding(text):
    return model.encode(text)

def article_text_embedding():
    datas = list(db_readData("WebInformation", "article", {}))
    data_embedding = []

    for data in datas:
        combined_content = ""
        article_title = data['title']
        for i, block in data['block'].items():
            combined_content += f"段落內容: {block['blockContent']}\n"
        for i, section in data['section'].items():
            combined_content += f"部分內容: {section['sectionContent']}\n"
        combined_content += "\n"

        article_embedding = text_embedding(combined_content)
        data_embedding.append((article_title, combined_content, article_embedding)) 
    return data_embedding

def cosine_similarity(embedding1, embedding2):
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

def find_most_relevant(qa_emb, article_emb):
    max_similarity = -1
    most_relevant = None
    most_relevant_title = None 

    for title, data, embedding in article_emb:
        similarity = cosine_similarity(qa_emb, embedding)
        if similarity > max_similarity:
            max_similarity = similarity
            most_relevant = data
            most_relevant_title = title 
    return most_relevant, most_relevant_title

def extract_content(content):
    content_str = ""
    if isinstance(content, dict):
        for key, value in content.items():
            content_str += extract_content(value)  
    elif isinstance(content, list):
        for item in content:
            content_str += extract_content(item)  
    else:
        content_str += str(content) + "\n"  
    return content_str

def generate_response(question, rel_content, type):
    global gpt_calls
    gpt_calls+=1
    question, synonym_term =synonym_analysis(question)
    if synonym_term!=[]:
        print("get_synonym\n")
        print("test:",question, " ",synonym_term)
        content_str = extract_content(rel_content) 
        filtered_content = []
        for line in content_str.splitlines():
            if synonym_term in line:
                if "；" in line:
                    filtered_content.append(line.split("；")[0])
                    continue  # 換下一段
                else:
                    filtered_content.append(line)
        filtered_content = "\n".join(filtered_content)
        print("filtered_content:",filtered_content)
        prompt = f"問題: {question}\n根據以下內容中有關{synonym_term}的資訊回答問題:\n{filtered_content}\n\n回答詳細問題:"
    else:
        if(type=="time1"):
            print("Need all content!")
            combined_content = ""
            combined_content += f"段落標題: {rel_content['title']}\n"
            combined_content += f"段落簡介: {rel_content['content']}\n"
            for i, block in rel_content['block'].items():
                combined_content += f"段落內容: {block['blockContent']}\n"
            for i, section in rel_content['section'].items():
                combined_content += f"段落內容: {section['sectionContent']}\n"
        elif(type=="time2"):
            print("get block content!")
            combined_content = rel_content        
        else:
            combined_content = rel_content
        prompt = f"問題: {question}\n\n根據以下內容生成符合問題的回答(麻煩反覆確認是否符合問題再輸出):\n{combined_content}\n\n回答:"
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.8,
        messages=[
            {"role": "system", "content": "你是一個專業的問題解答助手，請根據資料直接回答問題，不要提供額外的解釋或背景資訊。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def synonym_analysis(user_input):
    print("synonym_analysis")
    synonyms = db_readData("WebInformation","synonyms",{})
    
    if "E-dReg" in user_input:
        print("no replace!!")
        return user_input, []
    for synon in synonyms:
        if synon["term"] in user_input:
            user_input = user_input.replace(synon["term"], synon["vocabulary"])
            return user_input, synon["vocabulary"]
    return user_input, []

def extract_time(question):
    global gpt_calls
    gpt_calls+=1
    current_date = datetime.now()
    prompt = f"問題: {question}\n這是現在的日期:{current_date}\n請分析問題中的時間關鍵字（如「昨天」、「今天」、「上週」、「上個月」等），根據現在的日期推斷，並直接返回一個最符合時間關鍵字描述的日期值格式為('%Y-%m-%d')，該日期值必須是禮拜一。只需提供('%Y-%m-%d')，不需要任何額外解釋。"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.3,
        messages=[
            {"role": "system", "content": "你是一個專業的日期分析助手，僅回答 %Y-%m-%d，不需要其他解釋或文字。"},
            {"role": "user", "content": prompt}
        ]
    )
    date_values = response.choices[0].message.content.strip()
    print("date_values:",date_values)
    return date_values

def search_nearest_article(qa_time):
    qa_time = datetime.strptime(qa_time, "%Y-%m-%d")
    all_articles = list(db_readData("WebInformation","article",{}, {"title": 1})) 
    closest_article = None
    closest_date_diff = float('inf') 
    article_title=""

    for article in all_articles:
        title = article['title']
        article_date = extract_date_from_title(title)
        if article_date:
            date_diff = abs((qa_time - article_date).days)
            if date_diff <= 4:
                if date_diff < closest_date_diff:
                    closest_date_diff = date_diff
                    closest_article = article
                    article_title = title
    if closest_article:
        full_article = db_readData("WebInformation","article",{"_id": closest_article["_id"]},find_one=True)
        return full_article, article_title
    else:
        print("無法找到符合日期的相關文章")
        return search_latest_article()
    
def blockTitleAnalyze(question, nearest_article):
    print("blockTitle_analyze!")
    matched_block_content = ""
    for i, block in nearest_article['block'].items():
        flag = 0
        words = list(jieba.cut(block['blockTitle']))
        for idx, word in enumerate(words):
            if word in question:
                flag+=1
        if flag>=2:
            matched_block_content += block['blockTitle'] + ":" + block['blockContent'] + "\n"

    if matched_block_content:
        print("Matched Block Content Found!")
        print("matched_block_content:",matched_block_content)
        return generate_response(question, matched_block_content, "time2")
    else:
        print("No matching blockTitle found.")
        return generate_response(question, nearest_article, "time1")

def timeAnalyze(question, article_title):
    print("Got the time!")
    qa_time= extract_time(question)
    nearest_article, article_title = search_nearest_article(qa_time)
    print("QA's extract time:", qa_time,"  ",article_title)
    response = blockTitleAnalyze(question, nearest_article)
    article_title = article_title if article_title else "未知來源"
    print("\nAns:", response)
    final_answer = f"{response}"
    return final_answer, article_title

def bertModule(question, article_title):
    print("Bert Module")
    qa_embedding = text_embedding(question)
    article_embedding = article_text_embedding()
    relevant_content, article_title = find_most_relevant(qa_embedding, article_embedding)
    response = generate_response(question, relevant_content, "Bert")
    article_title = article_title if article_title else "未知來源"
    print("\nAns:", response)
    final_answer = f"{response}"
    return final_answer, article_title

def keywordAnalyze(question, article_title, classification):
    print("Keyword Analyze")
    appropriate_articles = search_articles(question)
    if appropriate_articles:
        article_title = appropriate_articles[0].get("title", "未知來源")
        responses = [article["response"] for article in appropriate_articles]
        answer = generate_answer(question, responses, classification)
    else:
        answer = "找不到符合問題的相關文章。"
        
    answer_traditional = converter.convert(answer)
    print("\nAns:", answer_traditional)
    final_answer = f"{answer_traditional}"
    return final_answer, article_title

def get_QA_analyze(user_input):
    global gpt_calls 
    gpt_calls = 0
    final_answer = ""
    start_time = time.time()
    article_title = "來源未知" 
    if user_input == "其他問題":
        return "請問你想問什麼問題 ? 麻煩詳細敘述 !"

    qa_classification = classify_question(user_input)
    print("QA's classification:", qa_classification)
    if classify_question_time(user_input):
        final_answer, article_title = timeAnalyze(user_input, article_title)
    else:
        if "數據型問題" in qa_classification:
            final_answer, article_title = bertModule(user_input, article_title)
        else:
            final_answer, article_title = keywordAnalyze(user_input, article_title, qa_classification)
            
    date_obj = extract_date_from_title(article_title)
    article_date = date_obj.strftime("%Y%m%d")

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total_running_time : {elapsed_time:.2f} s")
    print(f"Total GPT API calls: {gpt_calls}")
    return final_answer,article_title,article_date