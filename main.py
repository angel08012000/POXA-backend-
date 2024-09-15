from openai import OpenAI
from datetime import datetime
import time

from common import LASTEST, TOPICS, GET_NEWS_FAST, FORMAT_RESPONSE, FORMAT_NEWS, DB_LASTEST
from functions.week_summary import get_summary
from functions.get_QA_analyze import get_QA_analyze
from config import POXA

from database import r, store_news
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

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
def get_week_summary(date):
  print(f"送進來的日期: {date}")
  date = get_summary(date)

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
def get_define():
  res = []
  res.append(FORMAT_RESPONSE("text", {
    "content" : "尚未完成"
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
def get_qa_answer(question):
   answer = get_QA_analyze(question)

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
        "date": {
          "type": "string",
          "description": f"請要求使用者額外提供確切日期，若未提供年份、月份，請使用今天的年份、月份，今天是{datetime.today().strftime('%Y%m%d')}"
        }
      },
      "required": ["date"],
    }
  },
  {
    "name": "get_qa_answer",
    "description": "解答任何與台電電力交易市場相關的問題。如果使用者沒有明確要求本週摘要，應使用此功能。",
    "parameters": {
      "type": "object",
      "properties": {
        "question": {
          "type": "string",
          "description": "使用者所問的問題"
        }
      },
      "required": ["question"],
    }
  },
  {
    "name": "get_qa_question",
    "description": "當使用者點選QA問答、輸入QA問答時，麻煩使用者輸入想詢問的問題。",
    "parameters": {
      "type": "object",
      "properties": {
        "question": {
          "type": "string",
          "description": "麻煩使用者輸入想詢問的問題"
        }
      },
    }
  },
  
  {
    "name": "get_define",
    "description": "解釋各種專有名詞的定義",
    "parameters": {}
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
    app.run(debug=True)