import json
import logging
import os

import requests
from dotenv import load_dotenv
from flask import Flask, request

from api_elasticpath import get_catalog, get_token

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

load_dotenv()
logging.basicConfig(level=logging.DEBUG, format=FORMAT)

app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес.
    На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get(
        "hub.mode"
    ) == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get(
            "hub.verify_token"
        ) == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                # someone sent us a message
                if messaging_event.get("message"):
                    # the facebook ID of the person sending you the message
                    sender_id = messaging_event["sender"]["id"]
                    # the recipient's ID, which should be your page's FB ID
                    # recipient_id = messaging_event["recipient"]["id"]
                    # the message's text
                    message_text = messaging_event["message"]["text"]
                    send_menu(sender_id, message_text)
    return "ok", 200


def send_message(recipient_id, message_text):
    params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
    headers = {"Content-Type": "application/json"}
    request_content = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, headers=headers, data=request_content
    )
    response.raise_for_status()


def send_menu(recipient_id, message_text):
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    logger.debug(f'Client_id: {client_id}')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    logger.debug(f'access_token: {access_token}')
    goods = get_catalog('https://api.moltin.com/v2/products', access_token)
    logger.debug(f'goods: {goods}')
    params = {
        'access_token': os.getenv('PIZZA_SHOP_FB_TOKEN'),
    }
    json_data = {
        'recipient': {
            'id': recipient_id,
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': [
                        {
                            'title': 'Заголовок',
                            'subtitle': 'Описание',
                            'buttons': [
                                {
                                    'type': 'postback',
                                    'title': 'Тут будет кнопка',
                                    'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                                },
                            ],
                        }
                    ]
                },
            },
        },
    }
    params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
    # headers = {"Content-Type": "application/json"}
    # request_content = {
    #     "recipient": {
    #         "id": recipient_id
    #     },
    #     "message": {
    #         "text": message_text
    #     }
    # }
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, json=json_data
    )
    response.raise_for_status()


if __name__ == '__main__':
    app.run(debug=True)
