#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 創建Flask應用
app = Flask(__name__)

# LINE Bot設置
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 基本路由 - 確認服務運行中
@app.route('/')
def index():
    return "LINE Bot is running!"

# 處理LINE webhook
@app.route('/callback', methods=['POST'])
def callback():
    # 獲取X-Line-Signature標頭值
    signature = request.headers['X-Line-Signature']
    
    # 獲取請求體
    body = request.get_data(as_text=True)
    logger.info("Request body: %s", body)
    
    try:
        # 驗證簽名並處理請求
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)
    
    return 'OK'

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text
    
    # 簡單的回應邏輯
    if '你好' in text or '哈囉' in text:
        reply_text = "您好！我是法律諮詢助手，很高興為您服務。"
    elif '離婚' in text:
        reply_text = "關於離婚，台灣法律提供協議離婚和訴訟離婚兩種方式。您想了解哪一種？"
    else:
        reply_text = "謝謝您的提問。請問您想了解哪方面的法律問題？"
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# 啟動應用
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
