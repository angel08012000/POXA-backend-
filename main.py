from openai import OpenAI
import time
import requests
from datetime import datetime, timedelta
import os #Render

from common import FORMAT_RESPONSE, SHOW_MENU, ADD_FILE_LINKS
from functions.week_summary import get_summary
from functions.file_search import start_file_search
from functions.term_explaination import get_definition
from functions.get_QA_analyze import get_QA_analyze
from functions.get_etp_related import get_etp_related
from functions.team_related_QA import team_related_QA
from config import POXA

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
def get_week_summary(time):
  print(f"送進來的時間: {time}")
  time = get_summary(time)
  print(f"轉換後的時間: {time}")

  # 檢查時間
  if time == None:
      return [FORMAT_RESPONSE("text", {
          "tag": "span",
          "content": "時間過早/還沒到（第一篇摘要是 2023/10/2 發布）"
      })]

# 確定有摘要
  res = [
      FORMAT_RESPONSE("text", {
          "tag": "span",
          "content": "週摘要如下（註：每週摘要由週一發佈）"
      })
  ]
    
  # 查詢最新可用的連結
  while True:
      # 將日期合併成連結
      response = requests.get(f"{POXA}/report/{time}")
      
      if response.status_code == 200:
          res.append(FORMAT_RESPONSE("link", {
              "url": f"{POXA}/report/{time}",
              "content": f"{time}（點我查看）"
          }))
          break
      # 若未找到摘要，退回一週
      date = datetime.strptime(time, "%Y%m%d")
      date -= timedelta(days=7)
      time = date.strftime("%Y%m%d")

  return res + SHOW_MENU()

# 名詞解釋
def get_define(term_question):
  term = ""
  res = []
  for t in term_list:
     if t in term_question:
        term = t
        print("term: " + term)
        definition = get_definition(term)
        res.append(definition)
  if term == "":
    print("查無資料")
    # res = get_qa_answer(term_question)
    res.append("查無資料，請重新提問。")
   
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
    answer,article_title,article_date = get_QA_analyze(issue)

    res = []
    res.append(FORMAT_RESPONSE("text", {
        "content" : answer
      }))   
    if article_title or article_date:
      res.append(FORMAT_RESPONSE("link", {
                  "url": f"https://info.poxa.io/report/{article_date}",
                  "content": f"回答參考來源 : {article_title}"
        }))
    return res + SHOW_MENU()

#電力交易市場規則
def get_market_rule(rule_question):
  response = start_file_search(rule_question)
  res = []
  res.append(FORMAT_RESPONSE("text", {
      "content" : response
    }))
  
  links = ADD_FILE_LINKS(response)
  for key, value in links.items():
    res.append(FORMAT_RESPONSE("link", {
                "url": value,
                "content": f"\"{key}\"檔案連結"
            }))
  
  return res + SHOW_MENU()

#關於etp的問題
def get_etp_answer(etpProblem):
    answer = get_etp_related(etpProblem)

    if answer == False:
      print("no etp answer")
      qa_response = get_qa_answer(etpProblem)
      return qa_response
    else:
      res = []
      res.append(FORMAT_RESPONSE("text", {
          "content" : answer
        }))
    
      return res + SHOW_MENU()

def get_team_related(team_related):
    answer = team_related_QA(team_related)

    res = []
    res.append(FORMAT_RESPONSE("text", {
        "content" : answer
      }))
   
    return res + SHOW_MENU()


# define functions
today = datetime.today().strftime('%Y%m%d')
week = [
   {
    "name": "get_week_summary",
    "description": f"""
      提供電力交易市場的摘要。
      若給定日期，則使用該日期進行查詢。
      若有未給定年 or 月，請使用與「{datetime.today().strftime('%Y/%m/%d')}」對應的數字。
      若未給定日期，請回覆使用者以取得日期資訊。
      """,
    "parameters": {
      "type": "object",
      "properties": {
        "time": {
          "type": "string",
          "description": f"""
          跟時間有關的描述，不要推測使用者未提供的數據。
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
          """
        },
      },
      "required": ["time"],
    }
  },
]

file = [
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
]

define = [
  {
    "name": "get_define",
    "description": f"當使用者詢問單一專有名詞的定義時，請使用此功能。若非提到定義及解釋，請使用get_qa_answer。",
    "parameters": {
      "type": "object",
      "properties": {
        "term_question": {
          "type": "string",
          "description": "是單一專有名詞，代表使用者要問的名詞定義。"
        }
      },
      "required": ["term_question"],
    }
  },
]

other_question = [
  {
    "name": "get_qa_answer",
    "description": "接收所有使用者提出的完整問題，包括單一問題或多個問題。如果問題包含多個疑問句或其他複合內容，必須使用此功能。若使用者只是點選其他問答、輸入其他問答時，麻煩使用者輸入想詢問的問題。",
    "parameters": {
        "type": "object",
        "properties": {
            "issue": {
                "type": "string",
                "description": "完整接收使用者提出的問題（原始輸入），不得改寫或簡化，特別適用於包含多個問題的情況"
            }
        },
        "required": ["issue"]
    }
  },
  {
    "name": "get_etp_answer",
    "description": "當且僅當前端傳入的問題中，包含「得標量」、「結清」、「非交易」、「民營」關鍵詞，且問題為單一問題時，才使用此功能。如果問題包含多個問題或任何其他內容，請使用 get_qa_answer。",
    "parameters": {
        "type": "object",
        "properties": {
            "etpProblem": {
                "type": "string",
                "description": "完整接收包含「得標量」、「結清」、「非交易」、「民營」關鍵詞的單一問題"
            }
        },
        "required": ["etpProblem"]
    }
  },
  {
    "name": "get_team_related",
    "description": f"當使用者詢問POXAGPT或是團隊成員時，使用此功能。若尚未提及，請使用 get_qa_answer。",
    "parameters": {
      "type": "object",
      "properties": {
        "team_related": {
          "type": "string",
          "description": "使用者詢問的完整問題。"
        }
      },
      "required": ["team_related"],
    }
  }
]

client = OpenAI()

# flask
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def health_check():
    return "Service is running!", 200

@app.route('/greeting', methods=['GET'])
def greeting():
  return jsonify({
    "response": SHOW_MENU()
  })


@app.route('/chat', methods=['POST'])
def chat_with_bot():
  start_time = time.time()
  res = []

  data = request.json  # 拿到送來的參數
  if 'user' not in data:
    print("沒收到 user")
    return jsonify({'error': "Didn't receive what user said"}), 400

  if 'flow' not in data:
     print("沒收到 flow")
     return jsonify({'error': "Didn't receive what flow user want"}), 400

  print(f"前端的參數: {data}")

  messages = [{
    "role": "user",
    "content": data["user"]
  }]

  if data["flow"]=="摘要":
    functions = week
  
  elif data["flow"]=="法規問答":
    functions = file

  elif data["flow"]=="名詞解釋":
    functions = define
     
  elif data["flow"]=="其他問題":
    functions = other_question

  else:
    functions = week + file + define + other_question

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
    # app.run(host='0.0.0.0', debug=True)
    # port = int(os.environ.get("PORT", 5000))  # Render
    # print(f"Starting app on port {port}")
    app.run(host="0.0.0.0", port=5000)

