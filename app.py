from flask import Flask, request, abort, jsonify
from flask_cors import CORS
import redis
from google import genai
import re
import os
# from dotenv import load_dotenv
# load_dotenv()


from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    MessagingApiBlob,
    RichMenuSize,
    RichMenuRequest,
    RichMenuArea,
    RichMenuBounds,
    TemplateMessage,
    ButtonsTemplate,
    PostbackAction,
    MessageAction,
    QuickReply,
    QuickReplyItem,
    URIAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    TextMessageContent,
    FollowEvent
)

print(os.getenv('API_KEY'))
client = genai.Client(api_key=os.getenv('API_KEY'))
app = Flask(__name__)
CORS(app)
configuration = Configuration(access_token=os.getenv('ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('SECERT_KEY'))

def is_all_chinese(s):
    # 使用 fullmatch 確保整串字元都符合範圍
    pattern = r'^[\u4e00-\u9fa5]+$'
    return bool(re.fullmatch(pattern, s))

# @line_handler.add(PostbackEvent)
# def handle_postback(event):
#     userid=event.source.user_id
#     data=event.postback.data
#     #讀liff user id -> 建立關聯
#     if data=="liff":

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@app.route('/DB/save', methods=['POST'])
def save_user_data():
    # 1. 接收前端傳來的資料
    r = redis.from_url(os.getenv('KV_URL'), decode_responses=True)
    data = request.json
    user_id = data.get('userId')
    lang = data.get('lang')
    
    if not user_id:
        return jsonify({"error": "No User ID"}), 400

    # 2. 執行你原本想寫的 Python Redis 邏輯
    # 使用 Hash 結構存入多個欄位
    r.hset(f"{user_id}", mapping={
        "lang": lang
    })

    # 3. 順便讀取一下確認 (這就是你原本的 r.hgetall)
    saved_data = r.hgetall(f"{user_id}")
    print(f"User {user_id} updated: {saved_data}")

    # 4. 回傳成功訊息給前端
    return jsonify({"status": "success", "data": saved_data})

@app.route('/DB/get', methods=['POST'])
def get_data():
# 1. 接收前端傳來的資料
    r = redis.from_url(os.getenv('KV_URL'), decode_responses=True)
    data = request.json
    user_id = data.get('userId')
    preset_lang = data.get('lang')
    if not user_id:
        return jsonify({"error": "No User ID"}), 400

    # 3. 順便讀取一下確認 (這就是你原本的 r.hgetall)
    saved_data = r.hgetall(f"{user_id}")
    if saved_data=={}:
        print('in')
        r.hset(f"{user_id}", mapping={
        "lang": preset_lang
        })
        saved_data = r.hgetall(f"{user_id}")
        
    print(f"GET {user_id}, data: {saved_data}")

    # 4. 回傳成功訊息給前端
    return jsonify({"status": "success", "data": saved_data})

    

@line_handler.add(FollowEvent) #加好友
def handle_follow(event):
    print(f'got {event.type} event')


def create_rich_menu_1():
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_blob_api = MessagingApiBlob(api_client)

        areas = [
            RichMenuArea(
                bounds=RichMenuBounds(
                    x=0,
                    y=0,
                    width=1249,
                    height=1686
                ),
                action=URIAction(
                    label="開啟LIFF",
                    # uri = f"https://liff.line.me/2008641579-BdRYOWPn"
                    uri = os.getenv('LIFF_KEY')
                )
                
            )
        ]

        rich_menu_to_create = RichMenuRequest(
            size=RichMenuSize(
                width=2500,
                height=1686,
            ),
            selected=True,
            name="Mode",
            chat_bar_text="查看更多資訊",
            areas=areas
        )

        rich_menu_id = line_bot_api.create_rich_menu(
            rich_menu_request=rich_menu_to_create
        ).rich_menu_id

        with open('public/richmenu_1.jpg', 'rb') as image:
            line_bot_blob_api.set_rich_menu_image(
                rich_menu_id=rich_menu_id,
                body=bytearray(image.read()),
                _headers={'Content-Type': 'image/jpeg'}
            )

        line_bot_api.set_default_rich_menu(rich_menu_id)



@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        if '/set_language' in event.message.text:
            txt=event.message.text    
            print(txt.strip().split()[1])
            
        else:
            r = redis.from_url(os.getenv('KV_URL'), decode_responses=True)
            print("source:",event.source.user_id)
            saved_data = r.hgetall(f"{event.source.user_id}")
            if saved_data=={}:
                print('in')
                r.hset(f"{event.source.user_id}", mapping={
                "lang": "zh-TW"
                })
                saved_data = r.hgetall(f"{event.source.user_id}")

            if 'ja' in saved_data['lang']:
                MODE="japanese"
                
            elif 'en' in saved_data['lang']:
                MODE="english"
            else :
                MODE="traditional chinese"
            print("mode:",MODE)
            print("save_data:", saved_data['lang'])    
            # if not is_all_chinese(event.message.text):
            #     response = client.models.generate_content(
            #         model="gemini-2.5-flash",
            #         contents=f'({event.message.text}),help me to translate the words in brackets to traditional chinese,format just follow the original format,but reply without brackets'
            #     )
            # else:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f'({event.message.text}),help me to translate the words in brackets to {MODE},format just follow the original format,but reply without brackets'
            )
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response.text)]
                )
        )


create_rich_menu_1()
if __name__ == "__main__":

    app.run(port=5000,debug=True)
