import json
import logging
import os
import random

import requests
from dotenv import load_dotenv
from flask import Flask, request

from api_elasticpath import add_proudct_to_cart, get_cart, get_cart_products
from api_elasticpath import get_catalog, get_product_detail
from api_elasticpath import get_product_picture_url
from api_elasticpath import get_products_by_category_slug, get_token
from api_elasticpath import remove_products_from_cart
from database_backend import Database

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

load_dotenv()
logging.basicConfig(level=logging.DEBUG, format=FORMAT)

app = Flask(__name__)

LOGO_ID = '682e8af6-5d7a-4bb3-bb31-e1f1f8a858f3'
CATEGORY_LOGO_ID = 'b3f6ee38-ce6e-4273-8ead-ef103327b44b'
BASKET_LOGO_ID = '1e21b975-bd32-4cf1-9445-40ad420461f7'


def handle_users_reply(sender_id, message_text):
    database = Database(
        database_host=os.getenv('PIZZA_SHOP_DATABASE_HOST'),
        database_port=os.getenv('PIZZA_SHOP_DATABASE_PORT'),
        database_password=os.getenv('PIZZA_SHOP_DATABASE_PASSWORD')
    )
    states_functions = {
        'START': handle_start,
        'HANDLE_MENU': handle_order,
    }
    recorded_state = database.get(f'facebook_{sender_id}')
    logger.debug(f'Handle users reply: recorded state - {recorded_state}')
    if (not recorded_state
            or recorded_state.decode('utf-8') not in states_functions.keys()):
        user_state = 'START'
    else:
        user_state = recorded_state.decode('utf-8')
    if message_text == '/start':
        user_state = 'START'
    logger.debug(f'User_state: {user_state}')
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    database.set_(f'facebook_{sender_id}', next_state)


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


@app.route('/update', methods=['POST'])
def update_webhook():
    data = request.get_json()
    logger.debug(data)
    return 'ok', 200


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    logger.debug(data)
    if data["object"] == "page":
        logger.debug(f'Entry: {data["entry"]}')
        for entry in data["entry"]:
            logger.debug(f'Messaging: {entry["messaging"]}')
            for messaging_event in entry["messaging"]:
                logger.debug(f'Event: {messaging_event.get("message")}')
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    # recipient_id = messaging_event["recipient"]["id"]
                    message_text = messaging_event["message"]["text"]
                    logger.debug(
                        f'Main webhook - sender: {sender_id},'
                        f'message: {message_text}'
                    )
                    handle_users_reply(sender_id, message_text)
                if messaging_event.get('postback'):
                    sender_id = messaging_event["sender"]["id"]
                    # recipient_id = messaging_event["recipient"]["id"]
                    message_text = messaging_event["postback"]["payload"]
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


def handle_order(recipient_id, message_text):
    logger.debug('=====Handle Order======')
    logger.debug(f'Recipient: {recipient_id}')
    logger.debug(f'Message: {message_text}')
    message_text_string = json.loads(message_text)
    logger.debug(f'Handle start JSON: {message_text_string}')
    if message_text_string.get('category', None):
        send_menu('front_page', recipient_id)
        return 'START'
    if message_text_string.get('remove_from_basket'):
        product_to_remove = message_text_string.get('remove_from_basket')
        client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
        access_token = get_token(
            'https://api.moltin.com/oauth/access_token',
            client_id
        )
        cart = get_cart(
            'https://api.moltin.com/v2/carts/',
            access_token,
            str(recipient_id)
        )
        if cart:
            remove_products_from_cart(
                'https://api.moltin.com/v2/carts/',
                product_to_remove,
                access_token,
                str(recipient_id)
            )
        get_basket_menu(recipient_id)
        return 'HANDLE_MENU'
    if message_text_string.get('add_to_basket', None):
        logger.debug(message_text_string.get('add_to_basket', None))
        client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
        access_token = get_token(
            'https://api.moltin.com/oauth/access_token',
            client_id
        )
        cart = get_cart(
            'https://api.moltin.com/v2/carts/',
            access_token,
            str(recipient_id)
        )
        if cart:
            add_proudct_to_cart(
                'https://api.moltin.com/v2/carts/',
                message_text_string.get('add_to_basket', None),
                1,
                access_token,
                str(recipient_id)
            )
            json_data = {
                'recipient': {
                    'id': recipient_id,
                },
                'message': {
                    'text': 'Пицца добавлена в корзину'
                }
            }
            logger.debug(json_data)
            params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
            response = requests.post(
                "https://graph.facebook.com/v2.6/me/messages",
                params=params, json=json_data
            )
            response.raise_for_status()
        get_basket_menu(recipient_id)
        return 'HANDLE_MENU'
    return 'HANDLE_MENU'


def handle_start(recipient_id, message_text):
    logger.debug(f'Handle start - {message_text}')

    if message_text == '/start':
        message_text_string = dict()
        menu = 'front_page'
    else:
        try:
            message_text_string = json.loads(message_text)
            logger.debug(f'Handle start JSON: {message_text_string}')
        except json.decoder.JSONDecodeError:
            logger.debug(f'Error: {message_text}')
            return 'START'

    if message_text_string.get('category', None):
        menu = message_text_string.get('category')
    elif message_text_string.get('add_to_basket', None):
        logger.debug(
            "And add to basket:"
            f"{message_text_string.get('add_to_basket', None)}"
        )
        client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
        access_token = get_token(
            'https://api.moltin.com/oauth/access_token',
            client_id
        )
        cart = get_cart(
            'https://api.moltin.com/v2/carts/',
            access_token,
            str(recipient_id)
        )
        if cart:
            add_proudct_to_cart(
                'https://api.moltin.com/v2/carts/',
                message_text_string.get('add_to_basket', None),
                1,
                access_token,
                str(recipient_id)
            )
            json_data = {
                'recipient': {
                    'id': recipient_id,
                },
                'message': {
                    'text': 'Пицца добавлена в корзину'
                }
            }
            logger.debug(json_data)
            params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
            response = requests.post(
                "https://graph.facebook.com/v2.6/me/messages",
                params=params, json=json_data
            )
            response.raise_for_status()
        return 'START'
    elif message_text_string.get('basket', None):
        logger.debug('BASKET')
        get_basket_menu(recipient_id)
        return 'HANDLE_MENU'

    send_menu(menu, recipient_id)
    return 'START'


def send_menu(menu, recipient_id):
    database = Database(
        database_host=os.getenv('PIZZA_SHOP_DATABASE_HOST'),
        database_port=os.getenv('PIZZA_SHOP_DATABASE_PORT'),
        database_password=os.getenv('PIZZA_SHOP_DATABASE_PASSWORD')
    )
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
        menu
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
                    'payload': json.dumps(
                        {'basket': recipient_id}
                    ),
                },
                {
                    'type': 'postback',
                    'title': 'Акции',
                    'payload': json.dumps({"category": 'front_page'}),
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
                        'payload': json.dumps(
                            {"add_to_basket": full_pizza.get('id')}
                        ),
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
    logger.debug(
        'Our current categories: '
        f'{[category.get("slug") for category in categories.get("data")]}')
    category_buttons = [
        {
            'type': 'postback',
            'title': category.get('name'),
            'payload': json.dumps({"category": category.get('slug')}),
        } for category in categories.get('data')
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
    database.set_(menu, json.dumps(pizzas))
    logger.debug(f'Send CATEGORY {menu} CONTENT: {pizzas}')
    params = {
        'access_token': os.getenv('PIZZA_SHOP_FB_TOKEN'),
    }
    pizzas_new = database.get(menu).decode('utf-8')
    logger.debug(f'send_menu retrive menu: {json.dumps(pizzas_new)}')
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
                    'elements': pizzas_new,
                },
            },
        },
    }
    logger.debug(f'Send MENU JSON: {json_data}')
    params = {"access_token": os.environ["PAGE_ACCESS_TOKEN"]}
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, json=json_data
    )
    response.raise_for_status()


def get_basket_menu(recipient_id):
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    logger.debug(f'access_token: {access_token}')
    goods = get_cart_products(
        'https://api.moltin.com/v2/carts/',
        access_token,
        str(recipient_id)
    )

    picture_url = get_product_picture_url(
        'https://api.moltin.com/v2/files/',
        BASKET_LOGO_ID,
        access_token
    )
    logger.debug(f'Goods: {goods}')
    pizzas = [
        {
            'title': 'Меню',
            'image_url': picture_url,
            'subtitle': 'Здесь вы можете выбрать один из вариантов',
            'buttons': [
                {
                    'type': 'postback',
                    'title': 'Самовывоз',
                    'payload': json.dumps(
                        {'basket': recipient_id}
                    ),
                },
                {
                    'type': 'postback',
                    'title': 'Доставка',
                    'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                },
                {
                    'type': 'postback',
                    'title': 'В меню',
                    'payload': json.dumps({'category': 'front_page'}),
                },
            ],
        }
    ]
    for full_pizza in goods.get('data'):
        pizzas.append(
            {
                'title': (
                    f"{full_pizza.get('name')} "
                    f"({full_pizza.get('value').get('amount')} руб.)"
                ),
                'image_url': full_pizza.get('image').get('href'),
                'subtitle': full_pizza.get('description'),
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'Добавить еще одну',
                        'payload': json.dumps(
                            {"add_to_basket": full_pizza.get('product_id')}
                        ),
                    },
                    {
                        'type': 'postback',
                        'title': 'Убрать из корзины',
                        'payload': json.dumps(
                            {"remove_from_basket": full_pizza.get('id')}
                        ),
                    },
                ],
            }
        )
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
