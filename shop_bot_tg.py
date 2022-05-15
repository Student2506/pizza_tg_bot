"""
Работает с этими модулями:

python-telegram-bot==13.11
redis==4.3.0
"""
import logging
import os
from textwrap import dedent

import redis
from dotenv import load_dotenv
from geopy.distance import distance
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler
from telegram.ext import Filters, MessageHandler, Updater
from telegram.utils.helpers import escape_markdown

from api_elasticpath import add_proudct_to_cart, create_customer_record
from api_elasticpath import get_cart, get_cart_products, get_catalog
from api_elasticpath import get_pizzeries_coordinates, get_product_detail
from api_elasticpath import get_product_picture_url, get_token
from api_elasticpath import remove_products_from_cart
from api_yandex import fetch_coordinates

_database = None
logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def start(update: Update, context: CallbackContext) -> str:
    logger.debug('HANDLE_START')
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    logger.debug(f'access_token: {access_token}')
    goods = get_catalog('https://api.moltin.com/v2/products', access_token)
    logger.debug(f'goods: {goods}')
    keyboard = [[InlineKeyboardButton(
        good.get('name'), callback_data=good.get('id')
    )] for good in goods.get('data', None)]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose: ', reply_markup=reply_markup)
    return "HANDLE_MENU"


def handle_menu(update: Update, context: CallbackContext) -> str:
    logger.debug('HANDLE_MENU')
    query = update.callback_query
    logger.debug(query.data)
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    pizza = get_product_detail(
        'https://api.moltin.com/v2/products/',
        query.data,
        access_token
    )
    logger.debug(pizza)
    price_formatted = (
        pizza
        .get('price')[0]
        .get('amount')
    )
    pizza_detail = f'''
    *{escape_markdown(pizza.get('name'), version=2)}*
    Стоимость: *{price_formatted}* рублей

    _{escape_markdown(pizza.get('description'), version=2)}_
    '''
    context.bot.delete_message(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id
    )
    context.user_data['chosen'] = query.data
    keyboard = [[InlineKeyboardButton(
        'Положить в корзину', callback_data=f"add {pizza.get('id')}"
    ), ], ]
    keyboard.append([InlineKeyboardButton('Назад', callback_data='Back'), ])
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='Basket')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    pizza_picture_id = None
    if pizza.get("relationships"):
        pizza_picture_id = (
            pizza
            .get("relationships")
            .get("main_image")
            .get("data")
            .get("id")
        )

    if pizza_picture_id:
        url = get_product_picture_url(
            'https://api.moltin.com/v2/files/',
            pizza_picture_id,
            access_token
        )
        query.message.reply_photo(
            url,
            caption=dedent(pizza_detail),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        query.message.reply_text(
            text=dedent(pizza_detail),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    return 'HANDLE_DESCRIPTION'


def build_pizzas_menu(pizzas):
    logger.debug('HANDLE PIZZAS MENU')
    keyboard = []
    product_cart = ''
    for pizza in pizzas:
        price = pizza.get('meta').get('display_price').get('with_tax')
        product_cart += f'''
            *{escape_markdown(pizza.get('name'), version=2)}*
            {escape_markdown(pizza.get('description'), version=2)}
            {pizza.get('quantity')} пицц в корзине на сумму *{
                escape_markdown(
                    price.get('value').get('formatted'), version=2
                )
            }*

            '''

        keyboard.append([InlineKeyboardButton(
            f"Убрать из корзины {pizza.get('name')}",
            callback_data=pizza.get('id')
        )])
    logger.debug(product_cart)
    return product_cart, keyboard


def handle_description(update: Update, context: CallbackContext) -> str:
    logger.debug('Handle description')
    query = update.callback_query
    good = context.user_data.get("chosen")
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    logger.debug(f'access_token: {access_token}')
    user_choice = query.data
    logger.debug(f'handle_desc: {user_choice}')
    logger.debug(f'handle_desc: {query}')
    logger.debug(f'handle_desc: (choses) {good}')
    if user_choice == 'Back':
        goods = get_catalog('https://api.moltin.com/v2/products', access_token)
        logger.debug(f'goods: {goods}')
        keyboard = [[InlineKeyboardButton(
            good.get('name'), callback_data=good.get('id')
        )] for good in goods.get('data', None)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        logger.debug(query.message)
        query.message.reply_text('Please choose: ', reply_markup=reply_markup)
        return 'HANDLE_MENU'
    elif 'add' in user_choice:
        query.answer(text='Пицца добавлена в корзину', show_alert=False)
        logger.debug(user_choice)
        cart = get_cart(
            'https://api.moltin.com/v2/carts/',
            access_token,
            str(update.effective_user.id)
        )
        logger.debug('have a cart')
        cart = add_proudct_to_cart(
            'https://api.moltin.com/v2/carts/',
            good,
            1,
            access_token,
            str(update.effective_user.id)
        )
        logger.debug(f'added products: {cart}')
    else:
        products = get_cart_products(
            'https://api.moltin.com/v2/carts/',
            access_token,
            str(update.effective_user.id)
        )

        product_cart, keyboard = build_pizzas_menu(products.get('data'))
        keyboard.append(
            [InlineKeyboardButton('В меню', callback_data='menu'), ]
        )
        keyboard.append(
            [InlineKeyboardButton('Оплата', callback_data='pay'), ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        total_formatted = (
            products
            .get('meta')
            .get('display_price')
            .get('with_tax')
            .get('formatted')
        )
        product_cart += (
            f"*К оплате: {escape_markdown(total_formatted, version=2)}*"
        )
        logger.debug(dedent(product_cart))
        query.message.reply_text(
            text=dedent(product_cart),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        logger.debug(f'elseseee2 {products}')
    return 'HANDLE_CART'


def handle_cart(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    logger.debug(f'Handle CART {query.data}')
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    if query.data in ('menu', 'Back'):
        logger.debug('going to menu')
        goods = get_catalog('https://api.moltin.com/v2/products', access_token)
        logger.debug(f'goods: {goods}')
        keyboard = [[InlineKeyboardButton(
            good.get('name'), callback_data=good.get('id')
        )] for good in goods.get('data', None)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text('Please choose: ', reply_markup=reply_markup)
        return 'HANDLE_MENU'
    elif query.data == 'Basket':
        products = get_cart_products(
            'https://api.moltin.com/v2/carts/',
            access_token,
            str(update.effective_user.id)
        )

        product_cart, keyboard = build_pizzas_menu(products.get('data'))
        keyboard.append(
            [InlineKeyboardButton('В меню', callback_data='menu'), ]
        )
        keyboard.append(
            [InlineKeyboardButton('Оплата', callback_data='pay'), ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        total_formatted = (
            products
            .get('meta')
            .get('display_price')
            .get('with_tax')
            .get('formatted')
        )
        product_cart += (
            f"*К оплате: {escape_markdown(total_formatted, version=2)}*"
        )
        query.message.reply_text(
            text=dedent(product_cart),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return 'HANDLE_CART'
    elif query.data == 'pay':
        query.message.reply_text(
            'Хорошо. пришлите нам ваш адрес текстом или геолокацию.'
        )
        return 'HANDLE_WAITING'
    else:
        remove_products_from_cart(
            'https://api.moltin.com/v2/carts/',
            query.data,
            access_token,
            str(update.effective_user.id)
        )
        products = get_cart_products(
            'https://api.moltin.com/v2/carts/',
            access_token,
            str(update.effective_user.id)
        )
        product_cart, keyboard = build_pizzas_menu(products.get('data'))
        keyboard.append(
            [InlineKeyboardButton('В меню', callback_data='menu'), ]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        price_formatted = (
            products
            .get('meta')
            .get('display_price')
            .get('with_tax')
            .get('formatted')
        )
        product_cart += (
            f"*К оплате: {escape_markdown(price_formatted, version=2)}*"
        )
        logger.debug(product_cart)
        query.message.reply_text(
            text=dedent(product_cart),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return 'HANDLE_CART'


def handle_waiting(update: Update, context: CallbackContext) -> None:
    logger.debug('Handle waiting')
    location = update.message.location
    users_reply = update.message.text
    if location is not None:
        logger.debug(location)
    if users_reply is not None:
        yandex_api_key = os.getenv('PIZZA_SHOP_YA_TOKEN')
        location = fetch_coordinates(yandex_api_key, users_reply)
        logger.debug(location)
    if location is not None:
        current_position = location.latitude, location.longitude
    else:
        update.message.reply_text(
            'Не удалось определить адрес. Попробуйте ещё раз.'
        )
        return 'HANDLE_WAITING'
    logger.debug(current_position)
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    pizzeries = get_pizzeries_coordinates(
        'https://api.moltin.com/v2/flows/pizzeria/entries',
        access_token
    )
    logger.debug(pizzeries)
    closest_pizzeria = get_closest_pizzeria(location, pizzeries)
    context.user_data['pizzeria'] = closest_pizzeria
    context.user_data['user_coordinates'] = location
    logger.debug(closest_pizzeria)
    response, markup = get_delivery_model(closest_pizzeria)
    logger.debug(response)
    reply_markup = InlineKeyboardMarkup(markup)
    update.message.reply_text(dedent(response), reply_markup=reply_markup)
    return 'HANDLE_DELIVERY'


def handle_delivery(update: Update, context: CallbackContext) -> None:
    logger.debug('Handle delivery')
    query = update.callback_query
    logger.debug(query.data)
    nearest_pizzeria = context.user_data.get("pizzeria")
    logger.debug(nearest_pizzeria)
    if query.data == 'pickup':
        query.message.reply_text(
            escape_markdown(
                'Ваша пицца будет вас ждать по адресу:\n'
                f'{nearest_pizzeria.get("address")} \n'
                'До встречи в пиццерии 😁',
                version=2),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        location = context.user_data.get('user_coordinates')
        logger.debug(f'sending {location}')

    return 'HANDLE_DELIVERY'


def get_delivery_model(pizzeria):
    response = {
        'less_than_5_km': (
            '''
            Похоже, придется ехать до вас на самокате.
            Доставка будет стоить 100 рублей. Доставляем или самовывоз?'
            '''
        ),
        'less_than_500_m': (
            'Mожет, заберете пиццу из нашей пиццерии неподалёку? Она всего в '
            f'{pizzeria.get("distance").m:.2f} метрах от вас! вот её адрес: '
            f'{pizzeria.get("address")} \n\n'
            'А можем и бесплатно доставить, нам не сложно.'
        ),
        'less_than_20_km': 'Доставка будет стоить 300 рублей.',
        'more_than_20_km': (
            'Простите, но так далеко мы пиццу не доставим.\n'
            f'Ближайшая пиццерия аж в {pizzeria.get("distance").km:.2f} '
            'километрах от вас!'
        )
    }

    if pizzeria.get('distance').m < 500:
        message = response['less_than_500_m']
        markup = [
            [InlineKeyboardButton('Доставка', callback_data='delivery'), ],
            [InlineKeyboardButton('Самовывоз', callback_data='pickup'), ]
        ]
    elif pizzeria.get('distance').m < 5000:
        message = response['less_than_5_km']
        markup = [
            [InlineKeyboardButton('Доставка', callback_data='delivery'), ],
            [InlineKeyboardButton('Самовывоз', callback_data='pickup'), ]
        ]
    elif pizzeria.get('distance').m < 20000:
        message = response['less_than_20_km']
        markup = [
            [InlineKeyboardButton('Доставка', callback_data='delivery'), ],
            [InlineKeyboardButton('Самовывоз', callback_data='pickup'), ]
        ]
    else:
        message = response['more_than_20_km']
        markup = [
            [InlineKeyboardButton('Самовывоз', callback_data='pickup'), ]
        ]
    return message, markup


def get_pizzeriza_range(pizzeria):
    return pizzeria.get('distance').m


def get_closest_pizzeria(coords, pizzeries):
    pizzeria_distances = []
    for pizzeria in pizzeries:
        pizza_distance = distance(
            (coords.latitude, coords.longitude),
            (pizzeria.get('latitude'), pizzeria.get('longitude'))
        )
        pizzeria_range = {
            'name': pizzeria.get('alias'),
            'distance': pizza_distance,
            'address': pizzeria.get('address')
        }
        pizzeria_distances.append(pizzeria_range)
    return min(pizzeria_distances, key=get_pizzeriza_range)


def waiting_email(update: Update, context: CallbackContext) -> None:
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    user_to_order = (
        f'{update.effective_user.last_name} {update.effective_user.first_name}'
    )
    logger.debug(user_to_order)
    create_customer_record(
        'https://api.moltin.com/v2/customers',
        access_token,
        user_to_order,
        users_reply
    )
    return "START"


def handle_users_reply(update: Update, context: CallbackContext) -> None:
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': waiting_email,
        'HANDLE_WAITING': handle_waiting,
        'HANDLE_DELIVERY': handle_delivery,
    }
    state_handler = states_functions[user_state]
    try:
        logger.debug(f'Getting into {user_state}')
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        logger.error(err)


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.getenv("PIZZA_SHOP_DATABASE_PASSWORD")
        database_host = os.getenv("PIZZA_SHOP_DATABASE_HOST")
        database_port = os.getenv("PIZZA_SHOP_DATABASE_PORT")
        _database = redis.Redis(
            host=database_host, port=database_port, password=database_password
        )
    return _database


def main():
    load_dotenv()
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    token = os.getenv("PIZZA_SHOP_TG_BOTID")
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(
        MessageHandler(Filters.text | Filters.location, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()


if __name__ == '__main__':
    main()
