from openai import OpenAI
from datetime import datetime
import time

from common import LASTEST, TOPICS, GET_NEWS_FAST, FORMAT_RESPONSE, FORMAT_NEWS, DB_LASTEST
from functions.week_summary import get_summary
from functions.qa_consult import GET_COMMON_QA
from functions.file_search import start_file_search
from functions.term_explaination import get_definition
from functions.get_QA_analyze import get_QA_analyze
from functions.get_etp_related import get_etp_related
from config import POXA

from database import r, store_news
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

term_list = ['平台成員', '合格交易者', '電力交易單位', '電力調度單位', '資源', '併網型儲能設備', '交易資源', '報價代碼', '參與容量', '報價容量', '結清價格', '交易表計', '電能移轉', '能力測試', '調度日', '日', '需求公告', '合格交易者提出報價', '最佳化排程作業', '公布競價結果', '交易結果結算', '調頻備轉容量', '移轉複合動態調節備轉容量', '即時備轉容量', '補充備轉容量', '交易媒合期間', '資訊閉鎖期間', '需求量及供給量公告', '交易媒合結果公告', '成交紀錄公布', '標售資訊設定期間', '標售資訊審查期間', '買方競價期間', '應', '容量費', '效能費', '服務品質指標', '容量費', '效能費', '電能服務費', '效能費', '電能費', '容量費', '服務品質指標', '電能費', '補償價格', '電力交易單位', '發電機組發電機組', '自用發電設備自用發電設備', '需量反應需量反應', '併網型儲能設備儲能設備', '執行事件期間', '光儲合一', '光儲無限套娃']

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

# 本週摘要
def get_week_summary(time=None):
  print(f"送進來的時間: {time}")
  date = get_summary(time)

  if date == None:
    res = []
    res.append(FORMAT_RESPONSE("text", {
      "tag" : "span",
      "content" : f"時間過早/還沒到（第一篇摘要是 2023/10/2 發布）"
    }))
    return res

  res = []
  res.append(FORMAT_RESPONSE("text", {
    "tag" : "span",
    "content" : f"週摘要如下（註：每週摘要由週一發佈）"
  }))

  res.append(FORMAT_RESPONSE("link", {
    "url": f"{POXA}/report/{date}",
    "content": f"{date}（點我查看）"
  }))

  return res

# 名詞解釋
def get_define(term_question):
  term = ""
  for t in term_list:
     if t in term_question:
        term = t
        print("term: " + term)
        definition = get_definition(term)
  if term == "":
    print("查無資料")
    definition = start_file_search(term_question)

  res = []
  res.append(FORMAT_RESPONSE("text", {
    "content" : definition
  }))
   
  return res

#獲取使用者問題
def get_qa_question():
    res = []
    res.append(FORMAT_RESPONSE("text", {
        "tag": "span",
        "content": "請問您想詢問什麼問題呢？"
    }))
    return res

# QA 問答
def get_qa_answer(issue):
   answer = get_QA_analyze(issue)

   res = []
   res.append(FORMAT_RESPONSE("text", {
        "content" : answer
      }))
   
   return res

#電力交易市場規則
def get_market_rule(rule_question):
  response = start_file_search(rule_question)
  res = []
  res.append(FORMAT_RESPONSE("text", {
      "content" : response
    }))
  
  return res
#關於etp的問題
def get_etp_answer(etpProblem):
    answer = get_etp_related(etpProblem)

    res = []
    res.append(FORMAT_RESPONSE("text", {
        "content" : answer
      }))
   
    return res

# define functions
functions = [
  {
    "name": "get_week_summary",
    "description": "提供指定日期的台電電力交易市場的週摘要",
    "parameters": {
      "type": "object",
      "properties": {
        "time": {
          "type": "string",
          "description": f"""跟時間有關的描述，不要推測使用者未提供的數據。
          若有未給定年 or 月，請使用與「{datetime.today().strftime('%Y/%m/%d')}」對應的數字。
          若未給定日期，請保持空白。
          """
        },
      },
      # "required": ["time"],
    }
  },
  {
    "name": "get_qa_answer",
    "description": "解答任何使用者問題。",
    "parameters": {
      "type": "object",
      "properties": {
        "issue": {
          "type": "string",
          "description": "使用者所問的任何問題"
        }
      },
      "required": ["issue"],
    }
  },
  {
    "name": "get_market_rule",
    "description": "解釋電力交易市場的法規或市場規則。若非法規或市場規則，請使用get_qa_answer。",
    "parameters": {
      "type": "object",
      "properties": {
        "rule_question": {
          "type": "string",
          "description": "是特定的法規或市場規則，請不要修改使用者的問題。"
        }
      },
      "required": ["rule_question"],
    }
  }, 
  {
    "name": "get_qa_question",
    "description": "當使用者點選QA問答、輸入QA問答時，麻煩使用者輸入想詢問的問題，其他問題或動作，不要使用此功能。",
    "parameters": {
      "type": "object",
      "properties": {
        "question": {
          "type": "string",
          "description": "當使用者點選QA問答、輸入QA問答時，麻煩使用者輸入想詢問的問題。"
        }
      }
    }
  },
  {
    "name": "get_etp_answer",
    "description": "當使用者的問題完全涉及得標量、結清、非交易、或提到民營時，使用此功能。",
    "parameters": {
      "type": "object",
      "properties": {
        "etpProblem": {
          "type": "string",
          "description": "必須包含得標量、結清、非交易、或民營等關鍵詞的問題"
        }
      },
        "required": ["etpProblem"],
    }
  },
  {
    "name": "get_define",
    "description": f"當使用者詢問單一專有名詞的定義時，請使用此功能。若非提到定義及解釋，請使用get_qa_answer。",
    "parameters": {
      "type": "object",
      "properties": {
        "term_question": {
          "type": "string",
          "description": "是單一專有名詞，代表使用者要問的名詞定義。請勿修改使用者的問題。"
        }
      },
      "required": ["term_question"],
    }
  }
]

client = OpenAI()

# messages = []

# flask
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/greeting', methods=['GET'])
def greeting():
  res = []
  res.append(FORMAT_RESPONSE("text", {
    "tag" : "span",
    "content" : f"您好～ 我是電力交易市場小助手，我能夠提供以下功能:"
  }))

  res.append(FORMAT_RESPONSE("button", {
    "content": "每週摘要",
    "function": "get_week_summary"
  }))

  res.append(FORMAT_RESPONSE("button", {
    "content": "名詞解釋",
    "function": "get_define"
  }))

  res.append(FORMAT_RESPONSE("button", {
    "content": "QA 問答",
    "function": "get_qa_answer"
  }))

  res.append(FORMAT_RESPONSE("button", {
    "content": "規則查詢",
    "function": "get_market_rule"
  }))

  return jsonify({
    "response": res
  })

@app.route('/chat', methods=['POST'])
def chat_with_bot():
  start_time = time.time()
  res = []

  data = request.json  # 拿到送來的參數
  if 'user' not in data:
    return jsonify({'error': "Didn't receive what user said"}), 400

  messages = [{
    "role": "user",
    "content": data["user"]
  }]

  response = client.chat.completions.create(
    model="gpt-3.5-turbo", 
    messages= messages,
    functions = functions
  )

  res_mes = response.choices[0].message
  content = res_mes.content
  function_call = res_mes.function_call

  print(f"function_call: {function_call}")

  # gpt 直接回覆
  if content != None:
    # print(f"機器人1: {content}")
    res.append(FORMAT_RESPONSE("text", {
      "tag" : "span",
      "content" : content
    }))
    return jsonify({
      'response': res
    })
  
  if function_call: # 需要呼叫 function
    print(f"呼叫函式的名稱: {function_call.name}")
    print(f"呼叫函式的參數: {function_call.arguments}")

    final_res = call_function_by_name(function_call.name, eval(function_call.arguments))
    # print(f"最終結論: {data}")

    end_time = time.time()
    execution_time = end_time - start_time
    print(f">>>>>>>> 本輪對話花費時間: {execution_time}")
    
    return jsonify({'response': final_res})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
