import json
import logging
import os
import random

import requests
from dotenv import load_dotenv
from flask import Flask, request

from api_elasticpath import get_catalog, get_product_detail
from api_elasticpath import get_product_picture_url
from api_elasticpath import get_products_by_category_slug, get_token
from database_backend import get_database_connection

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

load_dotenv()
logging.basicConfig(level=logging.DEBUG, format=FORMAT)

app = Flask(__name__)

LOGO_ID = '682e8af6-5d7a-4bb3-bb31-e1f1f8a858f3'
CATEGORY_LOGO_ID = 'b3f6ee38-ce6e-4273-8ead-ef103327b44b'


def handle_users_reply(sender_id, message_text):
    DATABASE = get_database_connection()
    states_functions = {
        'START': handle_start,
    }
    recorded_state = DATABASE.get(sender_id)
    if (not recorded_state
            or recorded_state.decode('utf-8') not in states_functions.keys()):
        user_state = 'START'
    else:
        user_state = recorded_state.decode('utf-8')
    if message_text == '/start':
        user_state = 'START'
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    DATABASE.set(sender_id, next_state)


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
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]
                    message_text = messaging_event["message"]["text"]

                    handle_users_reply(sender_id, message_text)
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


def handle_start(recipient_id, message_text):
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    logger.debug(f'Client_id: {client_id}')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    logger.debug(f'access_token: {access_token}')
    goods = get_products_by_category_slug(
        'https://api.moltin.com/v2/categories',
        access_token,
        'front_page'
    )
    logger.debug(f'Front page category: {goods}')
    picture_url = get_product_picture_url(
        'https://api.moltin.com/v2/files/',
        LOGO_ID,
        access_token
    )
    pizzas = [
        {
            'title': 'Меню',
            'image_url': picture_url,
            'subtitle': 'Здесь вы можете выбрать один из вариантов',
            'buttons': [
                {
                    'type': 'postback',
                    'title': 'Корзина',
                    'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                },
                {
                    'type': 'postback',
                    'title': 'Акции',
                    'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                },
                {
                    'type': 'postback',
                    'title': 'Сделать заказ',
                    'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                },
            ],
        }
    ]
    for pizza in goods[0].get('relationships').get('products').get('data'):
        full_pizza = get_product_detail(
            'https://api.moltin.com/v2/products/',
            pizza.get('id'),
            access_token
        )
        picture_url = get_product_picture_url(
            'https://api.moltin.com/v2/files/',
            full_pizza.get('relationships').get('main_image').get('data').get(
                'id'
            ),
            access_token
        )
        pizzas.append(
            {
                'title': (
                    f"{full_pizza.get('name')} "
                    f"({full_pizza.get('price')[0].get('amount')} руб.)"
                ),
                'image_url': picture_url,
                'subtitle': full_pizza.get('description'),
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'Добавить в корзину',
                        'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                    },
                ],
            }
        )
    picture_url = get_product_picture_url(
        'https://api.moltin.com/v2/files/',
        CATEGORY_LOGO_ID,
        access_token
    )
    categories = get_catalog(
        'https://api.moltin.com/v2/categories',
        access_token
    )
    logger.debug(categories)
    category_buttons = [
        {
            'type': 'postback',
            'title': category.get('name'),
            'payload': 'DEVELOPER_DEFINED_PAYLOAD',
        } for category in categories.get('data')[:-1]
    ]
    logger.debug(f'Categroy_buttons {category_buttons}')
    pizzas.append(
        {
            'title': 'Не нашли нужную пиццу?',
            'image_url': picture_url,
            'subtitle':
                'Остальные пиццы можно посмотреть в одной из категорий',
            'buttons': random.sample(category_buttons, 3),
        }
    )
    logger.debug(pizzas)
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
                    'image_aspect_ratio': 'square',
                    'elements': pizzas,
                },
            },
        },
    }
    logger.debug(json_data)
    params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, json=json_data
    )
    response.raise_for_status()


if __name__ == '__main__':
    app.run(debug=True)
