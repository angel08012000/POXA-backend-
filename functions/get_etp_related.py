import json, re
from openai import OpenAI
from pymongo.server_api import ServerApi
from datetime import datetime
from langchain_google_vertexai import ChatVertexAI

client = OpenAI()

def execute_code_logic(data, prefix, is_qse, suffix, gpt, gemini):
    try:
        total_value = 0
        count = 0
        max_value = float('-inf')
        min_value = float('inf')
        product_field = f"{prefix}{suffix}"
        qse_field = f"{prefix}{suffix}Qse" if is_qse else product_field
        target = gemini
        if qse_field==gpt and gemini!=gpt:
            target = qse_field

        for entry in data:
            if target in entry:
                value = entry[target]
                total_value += value
                count += 1

                if value > max_value:
                    max_value = value
                if value < min_value:
                    min_value = value

        if count > 0:
            avg_value = total_value / count
            return {
                "max_value": max_value,
                "min_value": min_value,
                "avg_value": avg_value
            }, qse_field
        else:
            return "無數據可供計算"

    except Exception as e:
        return f"執行代碼時出錯: {e}"

def classify_question(question):
    rule = """
    字首: 當問題提到E-dReg，prefix=edreg；提到調頻備轉，prefix=reg；提到即時備轉，prefix=sr；提到補充備轉，prefix=sup。
    字中: 當問題提到投標量，midfix=Offering；提到得標量，midfix=Bid；提到非交易，midfix=BidNontrade；提到結清價格，midfix=Price。
    字尾: 當問題中提到民營，suffix=Qse。若未提到則無suffix。
    輸出: 僅輸出 prefix+midfix+suffix，不需加入其他文字和解釋。
    """
    sample = """
    1. 問題：「請問調頻備轉的得標量？」 -> 輸出：regBid
    2. 問題：「民營的即時備轉結清價格是？」 -> 輸出：srPriceQse
    3. 問題：「補充備轉的結清價格？」 -> 輸出：supPrice
    4. 問題：「請問E-dReg非交易的得標量？」 -> 輸出：edregBidNontrade
    5. 問題：「民營調頻備轉投標量？」 -> 輸出：regOfferingQse
    6. 問題：「非交易調頻備轉的得標量？」 -> 輸出：regBidNontrade
    7. 問題：「即時備轉的投標量？」 -> 輸出：srOffering
    """

    # GPT
    prompt = f"""
    根據以下規則，判斷該問題查詢的資料庫項目，並嚴格按照格式「prefix+midfix+suffix」輸出結果。如果 suffix 不存在則略過 suffix。請只輸出資料庫項目，**不要加入任何解釋、引言、或其他文字**。
    
    問題：{question}
    
    規則:
    {rule}
    
    範例：
    {sample}
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[
            {"role": "system", "content": "你是一個專業的問題分析助手，請判斷問題符合規則哪點，並輸出欲查詢的資料庫項目。"},
            {"role": "user", "content": prompt}
        ]
    )
    answer = response.choices[0].message.content.strip()
    
    if "：" in answer or ":" in answer:
        answer = answer.split("：")[-1].strip()

    # Gemini
    llm = ChatVertexAI(
        model="gemini-1.5-pro",
        temperature=0,
        max_tokens=None,
        max_retries=6,
        stop=None,
    )
    messages = [(
            "system",
            f"""
            根據以下規則，判斷該問題查詢的資料庫項目，並嚴格按照格式「prefix+midfix+suffix」輸出結果。如果 suffix 不存在則略過 suffix。請只輸出資料庫項目，**不要加入任何解釋、引言、或其他文字**。

            規則:
            {rule}
            
            範例：
            {sample}
            """,
        ),("human", question),
    ]
    ai_msg = llm.invoke(messages)
    result = ai_msg.content

    # answer->GPT   result->Gemini
    return answer, result

def parse_and_find_closest(data_list, date_field):
    today = datetime.today()

    closest_date = None
    matching_list = []
    closest_date_diff = float('inf')

    for entry in data_list:
        entry_date_str = entry[date_field]
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d") 
        
        date_diff = abs((today - entry_date).days)

        if date_diff < closest_date_diff:
            closest_date_diff = date_diff
            closest_date = entry_date

    if closest_date:
        for entry in data_list:
            entry_date_str = entry[date_field]
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")

            if entry_date == closest_date:
                matching_list.append(entry)

    return matching_list

def parse_by_exact_date(data_list, date_field, exact_date):
    matching_list = []
    for entry in data_list:
        entry_date_str = entry[date_field]
        if entry_date_str == exact_date:
            matching_list.append(entry)
    return matching_list

def dateAnalyze(question):
    match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', question)
    if match:
        return match.group(0)
    return False

def get_etp_manu(user_input):
    info = "廠商:"
    check = dateAnalyze(user_input)
    print("date:", check)

    json_file = 'poxa-info.etp_qse_list_query.json'
    with open(json_file, 'r', encoding='utf-8') as f:
        manufacturer_data = json.load(f)

    manu_query = manufacturer_data[0]["query"]
    data = manu_query["data"]
    for i in range(len(data)):
        cap = data[i]['capacitySummary']
        capacity = cap['regresTotal'] + cap['spinresTotal'] + cap['suppresTotal'] + cap['edregTotal']
        info += f"{i+1}:{data[i]['plantName']}的參與容量是{capacity}MW。\n"
    # print(info)
    prompt = f"問題: {user_input}\n\n根據以下文章內容生成回答，若以下內容無法準確回答，即回覆資料不足即可\n文章內容:{info}"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.8,
        messages=[
            {"role": "system", "content": "你是一個專業的問題解答助手，你只會根據資料內容回答問題，不會提供額外的解釋和背景資訊，或是不存在於資料內容的回答。"},
            {"role": "user", "content": prompt}
        ]
    )

    llm = ChatVertexAI(
        model="gemini-1.5-pro",
        temperature=0,
        max_tokens=None,
        max_retries=6,
        stop=None,
    )

    messages = [(
            "system",
            f"""
            你是一個專業的問題解答助手，你只會根據資料內容回答問題，不會回答不存在於資料內容的資訊。
            你會根據以下資訊內容生成回答，若以下內容無法回答問題，你會回覆'無法回答該問題，請補充問題細節或換個問法。'。
            資訊內容:{info}
            """,
        ),("human", user_input),
    ]
    ai_msg = llm.invoke(messages)
    result = ai_msg.content

    return "GPT Ans:" + response.choices[0].message.content.strip() + "\n\nGemini Ans:" + result

def get_etp_related(user_input):
    classify_gpt, classify_gemini = classify_question(user_input)
    check = dateAnalyze(user_input)
    print("date:", check)
    fault = ""

    is_qse = "民營" in user_input

    if "即時備轉" in user_input:
        prefix = "sr"
    elif "調頻備轉" in user_input:
        prefix = "reg"
    elif "E-dReg" in user_input:
        prefix = "edreg"
    elif "補充備轉" in user_input:
        prefix = "sup"
    else:
        prefix = None

    if "非交易" in user_input:
        suffix = "BidNontrade"
    elif "結清價格" in user_input:
        suffix = "Price"
    elif "得標量" in user_input:
        suffix = "Bid"
    elif "投標量" in user_input:
        suffix = "Offering"
    else:
        suffix = None

    if suffix != "Offering":
        json_file = 'poxa-info.etp_settle_value_query.json'
        date = "tranDate"
    else:
        json_file = 'poxa-info.etp_offering.json'
        date = "date"
    print(f"Using JSON file: {json_file}")\
    
    if prefix and suffix is not None:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

            if check == False:
                print("check false!")
                search_data = parse_and_find_closest(existing_data, date)
            else:
                print("check true!")
                search_data = parse_by_exact_date(existing_data, date, check)
                if not search_data: 
                    print(f"未找到 {check} 的資料，改為查找最新日期。")
                    fault = f"未找到 {check} 的資料，改為查找最新日期。"
                    search_data = parse_and_find_closest(existing_data, date)
            lastest_result, classification = execute_code_logic(search_data, prefix, is_qse, suffix, classify_gpt, classify_gemini)
            print("GPT VS Gemini VS Actually classify: ", classify_gpt," VS ",classify_gemini," VS ",classification)
            if isinstance(lastest_result, dict):
                answer = (f"目前最新->{search_data[0][date]}的ETP資料:\n"
                          f"最大值: {lastest_result['max_value']:.2f}, "
                          f"最小值: {lastest_result['min_value']:.2f}, "
                          f"平均值: {lastest_result['avg_value']:.2f}\n")
            else:
                answer = lastest_result 
            if fault:
                answer += f"\n{fault}\n"
            print(f"回答: {answer}")
            return answer

        except FileNotFoundError:
            print(f"找不到檔案: {json_file}")
    else:
        print("無法解析您的問題，請確認輸入格式。")
        return False