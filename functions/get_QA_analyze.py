import re, opencc, time
from pymongo.server_api import ServerApi
from openai import OpenAI
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
from db_manager import db_readData

gpt_calls = 0
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

    for article in all_articles:
        title = article['title']
        article_date = extract_date_from_title(title)
        
        if article_date:
            date_diff = abs((current_date - article_date).days) 
            if date_diff < closest_date_diff:
                closest_date_diff = date_diff
                closest_article = article

    if closest_article:
        full_article = db_readData("WebInformation","article",{"_id": closest_article["_id"]},find_one=True)
        return full_article
    else:
        print("無法找到接近當前日期的文章")
        return None

def extract_keywords(question):
    global gpt_calls

    nouns = list(db_readData("WebInformation","definitions",{}))
    terms = [noun['term'] for noun in nouns]  
    terms_string = '、'.join(terms) 
 
    gpt_calls+=1
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

def classify_question_lastest(question):
    global gpt_calls
    gpt_calls += 1
    prompt = f"請判斷以下問題是否有明確提及到目前、當前、最近或最新之類的時間點：\n問題：{question}\n\n請回答是或否就好，無須回答其他額外資訊："
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.1,
        messages=[
            {"role": "system", "content": "你是一個專業的問題分類助手，請判斷問題是否有明確提及到當前或最新之類的時間點。"},
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

def analysis_questionTime(question):
    global gpt_calls
    gpt_calls+=1
    prompt = f"請分析以下問題是否包含明確的時間點：\n問題：{question}\n\n請回答是或否就好，無須回答其他額外資訊："
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "你是一個專業的問題分析師，請對問題進行分析，判斷該問題是否包含明確的時間點。"},
            {"role": "user", "content": prompt}
        ]
    )
    answer = response.choices[0].message.content.strip()
    if "是" in answer :
        return False
    else:
        return True

def search_articles(question):
    global gpt_calls
    keywords = extract_keywords(question)
    print("Keywords:", keywords)
    
    query = {"$text": {"$search": " ".join(keywords)}}
    results = db_readData("WebInformation","article",query)
    result_list=[]
    if results == []:
        print("Empty")
    else:
        for result in results:
            combined_content = ""

            combined_content += f"段落標題: {result['title']}\n"
            combined_content += f"段落簡介: {result['content']}\n"

            for i, block in result['block'].items():
                combined_content += f"段落內容: {block['blockContent']}\n"
            
            for i, section in result['section'].items():
                combined_content += f"部分內容: {section['sectionContent']}\n"
            combined_content += "\n"

            gpt_calls+=1
            prompt = f"問題: {question}\n\n根據以下內容生成最符合的回答，回答請在600字左右:\n{combined_content}\n\n回答:"
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                temperature=0.8,
                messages=[
                    {"role": "system", "content": "你是一個專業的問題解答助手，請根據資料直接回答問題，不要提供額外的解釋或背景資訊。"},
                    {"role": "user", "content": prompt}
                ]
            )
            result_list.append(response)
    return result_list

def generate_answer(question, article, classification):
    global gpt_calls

    ans_type = ""
    if "事實性問題" in classification:
        ans_type = "簡明"
    elif "意見性問題" in classification:
        ans_type = "詳細"
    elif "推理性問題" in classification:
        ans_type = "綜合"

    gpt_calls+=1
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
    datas = list(db_readData("WebInformation","article",{}))
    data_embedding = []

    for data in datas:
        combined_content = ""

        for i, block in data['block'].items():
            combined_content += f"段落內容: {block['blockContent']}\n"
        
        for i, section in data['section'].items():
            combined_content += f"部分內容: {section['sectionContent']}\n"
        combined_content += "\n"

        article_embedding = text_embedding(combined_content)
        data_embedding.append((combined_content, article_embedding))
    return data_embedding

def cosine_similarity(embedding1, embedding2):
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

def find_most_relevant(qa_emb, article_emb):
    max_similarity = -1
    most_relevant = None

    for data, embedding in article_emb:
        similarity = cosine_similarity(qa_emb, embedding)
        if similarity > max_similarity:
            max_similarity = similarity
            most_relevant = data
    return most_relevant

def generate_response(question, rel_content):
    global gpt_calls
    gpt_calls+=1
    prompt = f"問題: {question}\n\n根據以下內容生成合理的回答:\n{rel_content}\n\n回答:"
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
        return user_input

    for synon in synonyms:
        if synon["term"] in user_input:
            user_input = user_input.replace(synon["term"], synon["vocabulary"])
            break;
    
    return user_input

def get_QA_analyze(user_input):
    global gpt_calls
    final_answer = ""
    start_time = time.time()

    user_input = synonym_analysis(user_input)
    print(user_input);

    qa_classification = classify_question(user_input)
    print("QA's classification:", qa_classification)
    qa_analyzeTime = analysis_questionTime(user_input)
    print("QA's analyzeTime:", qa_analyzeTime)
    if "數據型問題" in qa_classification:
        if classify_question_lastest(user_input) or analysis_questionTime(user_input):
            print("search_latest_article")
            lastest_article = search_latest_article()
            response = generate_response(user_input, lastest_article)
        else:
            print("Bert Module")
            qa_embedding = text_embedding(user_input)
            article_embedding = article_text_embedding()
            relevant_content = find_most_relevant(qa_embedding, article_embedding)
            response = generate_response(user_input, relevant_content)
        print("\nAns:", response)
        final_answer = response
    else:
        if classify_question_lastest(user_input) or analysis_questionTime(user_input):
            print("search_latest_article")
            lastest_article = search_latest_article()
            answer = generate_answer(user_input, lastest_article, qa_classification)
        else:
            appropriate_articles = search_articles(user_input)
            answer = generate_answer(user_input, appropriate_articles, qa_classification)
        answer_traditional = converter.convert(answer)
        print("\nAns:", answer_traditional)
        final_answer = answer_traditional

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total_running_time : {elapsed_time:.2f} s")
    print(f"Total GPT API calls: {gpt_calls}")
    return final_answer