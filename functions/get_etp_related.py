import json
from openai import OpenAI
from pymongo.server_api import ServerApi
from functions.get_QA_analyze import get_QA_analyze
from datetime import datetime

client = OpenAI()

def execute_code_logic(data, prefix, is_qse, suffix):
    try:
        total_value = 0
        count = 0
        max_value = float('-inf')
        min_value = float('inf')


        for entry in data:
            product_field = f"{prefix}{suffix}"
            qse_field = f"{prefix}{suffix}Qse" if is_qse else product_field

            if qse_field in entry:
                value = entry[qse_field]
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
            }
        else:
            return "無數據可供計算"

    except Exception as e:
        return f"執行代碼時出錯: {e}"

def classify_question(question):
    rule = """
    字首: 當問題提到E-dReg，prefix=edreg；提到調頻備轉，prefix=reg；提到即時備轉，prefix=sr；提到補充備轉，prefix=sup。
    字中: midfix=Offering，當問題提到得標量，midfix=Bid；提到非交易，midfix=BidNontrade；提到結清價格，midfix=Price。
    字尾: 當問題中提到民營，suffix=Qse。若未提到則無suffix。
    輸出: 僅輸出 prefix+midfix+suffix，不需加入其他文字和解釋。
    """

    prompt = f"""
    根據以下規則，判斷該問題查詢的資料庫項目，並嚴格按照格式「prefix+midfix+suffix」輸出結果。如果 suffix 不存在則略過 suffix。請只輸出資料庫項目，**不要加入任何解釋、引言、或其他文字**。
    
    問題：{question}
    
    規則:
    {rule}
    
    範例：
    1. 問題：「請問調頻備轉的得標量？」 -> 輸出：regBid
    2. 問題：「民營的即時備轉結清價格是？」 -> 輸出：srPriceQse
    3. 問題：「補充備轉的結清價格？」 -> 輸出：supPrice
    4. 問題：「請問E-dReg非交易的得標量？」 -> 輸出：edregBidNontrade
    5. 問題：「民營調頻備轉？」 -> 輸出：regOfferingQse
    6. 問題：「非交易調頻備轉的得標量？」 -> 輸出：regBidNontrade
    """
    
    # 生成回答
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
    return answer

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

def get_etp_related(user_input):
    classify = classify_question(user_input)
    print("classify:", classify)

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
    else:
        suffix = "Offering"

    if suffix != "Offering":
        json_file = 'poxa-info.etp_settle_value_query.json'
        date = "tranDate"
    else:
        json_file = 'poxa-info.etp_offering.json'
        date = "date"

    print(f"Using JSON file: {json_file}")
    print("product_prefix:", prefix)
    print("suffix:", suffix)

    if prefix and suffix is not None:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

            closest_data = parse_and_find_closest(existing_data, date)
            lastest_result = execute_code_logic(closest_data, prefix, is_qse, suffix)
            if isinstance(lastest_result, dict):
                answer = (f"目前最新->{closest_data[0][date]}的ETP資料:\n"
                          f"最大值: {lastest_result['max_value']:.2f}, "
                          f"最小值: {lastest_result['min_value']:.2f}, "
                          f"平均值: {lastest_result['avg_value']:.2f}\n")
            else:
                answer = lastest_result 

            print(f"回答: {answer}")
            return answer

        except FileNotFoundError:
            print(f"找不到檔案: {json_file}")
    else:
        print("無法解析您的問題，請確認輸入格式。")
        return False