import logging
import os
from textwrap import dedent

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram import ParseMode, ShippingOption, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler
from telegram.ext import Filters, MessageHandler, PreCheckoutQueryHandler
from telegram.ext import ShippingQueryHandler, Updater
from telegram.utils.helpers import escape_markdown

from api_elasticpath import add_proudct_to_cart, create_customer_address
from api_elasticpath import get_cart, get_cart_products, get_catalog
from api_elasticpath import get_customer_address, get_pizzeries_coordinates
from api_elasticpath import get_product_detail, get_product_picture_url
from api_elasticpath import get_token, remove_products_from_cart
from api_yandex import fetch_coordinates
from database_backend import get_database_connection
from pizzeria import calculate_distance_and_price, get_closest_pizzeria

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
FEEDBACK_TIMER = 3600


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
        return 'HANDLE_DESCRIPTION'

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
    if 'add' in user_choice:
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
        return 'HANDLE_DESCRIPTION'

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
    if query.data == 'Basket':
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
    if query.data == 'pay':
        query.message.reply_text(
            'Хорошо. пришлите нам ваш адрес текстом или геолокацию.'
        )
        return 'HANDLE_WAITING'

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
    keyboard.append(
        [InlineKeyboardButton('Оплата', callback_data='pay'), ]
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
    if users_reply:
        yandex_api_key = os.getenv('PIZZA_SHOP_YA_TOKEN')
        location = fetch_coordinates(yandex_api_key, users_reply)
        logger.debug(location)
    if not location:
        update.message.reply_text(
            'Не удалось определить адрес. Попробуйте ещё раз.'
        )
        return 'HANDLE_WAITING'

    current_position = location.latitude, location.longitude
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
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    internal_access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id,
        client_secret=os.getenv('PIZZA_SHOP_CLIENT_SECRET', None)
    )
    context.user_data['user_coordinates'] = create_customer_address(
        'https://api.moltin.com/v2/flows/customer-address/entries',
        internal_access_token,
        location
    )
    logger.debug(closest_pizzeria)
    message_to_customer, markup, delivery_price = calculate_distance_and_price(
        closest_pizzeria
    )
    context.user_data['delivery'] = delivery_price
    logger.debug(message_to_customer)
    reply_markup = InlineKeyboardMarkup(markup)
    update.message.reply_text(
        dedent(message_to_customer), reply_markup=reply_markup
    )
    return 'HANDLE_DELIVERY'


def handle_delivery(
    update: Update, context: CallbackContext
) -> None:
    logger.debug('Handle delivery')
    query = update.callback_query
    logger.debug(query.data)
    nearest_pizzeria = context.user_data.get("pizzeria")
    logger.debug(nearest_pizzeria)
    if query.data == 'pickup':
        message = escape_markdown(
            'Ваша пицца будет вас ждать по адресу:\n'
            f'{nearest_pizzeria.get("pizzeria").get("address")}\n'
            'До встречи в пиццерии 😁',
            version=2)
    else:
        location = context.user_data.get('user_coordinates')
        logger.debug(f'sending {location}')
        client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
        access_token = get_token(
            'https://api.moltin.com/oauth/access_token',
            client_id
        )
        location = get_customer_address(
            'https://api.moltin.com/v2/flows/customer-address/entries',
            access_token,
            location
        )
        delivery_tg = nearest_pizzeria.get("pizzeria").get("delivery-tg-id")
        bot = update.callback_query.bot
        products = get_cart_products(
            'https://api.moltin.com/v2/carts/',
            access_token,
            str(update.effective_user.id)
        )
        product_cart, _ = build_pizzas_menu(products.get('data'))
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
        bot.send_message(
            delivery_tg,
            dedent(product_cart),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        bot.send_location(
            delivery_tg,
            latitude=location.get('latitude'),
            longitude=location.get('longitude')
        )
        logger.debug(f'get delivery id: {delivery_tg}')
        context.job_queue.run_once(
            remind_to_give_feedback,
            FEEDBACK_TIMER,
            context=query.message.chat_id
        )
        message = escape_markdown(
            'Вашу пиццу привезет курьер по указанному адресу:\n'
            'До встречи 😁',
            version=2)
    keyboard = [[InlineKeyboardButton(
        'Оплата', callback_data='payment_mode'
    ), ], ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup
    )

    return 'PAYMENT'


def remind_to_give_feedback(context: CallbackContext):
    message = '''
        Приятного аппетита! *место для рекламы*

        *сообщение что делать если пицца не пришла*
    '''
    context.bot.send_message(
        chat_id=context.job.context, text=dedent(message)
    )


def start_with_shipping_callback(
    update: Update, context: CallbackContext
) -> None:
    chat_id = update.callback_query.message.chat_id

    title = "Оплата заказа"
    description = "Оплата через API Telegram"
    payload = "Custom-Payload"
    provider_token = os.getenv('PIZZA_SHOP_PAY_TOKEN')
    currency = "RUB"
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id
    )
    products = get_cart_products(
        'https://api.moltin.com/v2/carts/',
        access_token,
        str(update.effective_user.id)
    )
    price = (
        products
        .get('meta')
        .get('display_price')
        .get('with_tax')
        .get('amount')
    )
    prices = [LabeledPrice(label="Заказ", amount=price * 100), ]

    context.bot.send_invoice(
        chat_id, title, description, payload,
        provider_token, currency, prices,
        need_name=True, need_phone_number=True,
        need_email=True, need_shipping_address=True,
        is_flexible=True)
    return 'SHIPPING_CALLBACK'


def shipping_callback(update: Update, context: CallbackContext) -> None:
    query = update.shipping_query
    if query.invoice_payload != 'Custom-Payload':
        context.bot.answer_shipping_query(
            shipping_query_id=query.id, ok=False,
            error_message="Something went wrong..."
        )
        return

    options = list()
    delivery = context.user_data.get('delivery')
    options.append(
        ShippingOption(
            '1', 'Доставка', [LabeledPrice('delivery', delivery * 100)]
        )
    )
    context.bot.answer_shipping_query(
        shipping_query_id=query.id, ok=True, shipping_options=options
    )


def precheckout_callback(update: Update, context: CallbackContext) -> None:
    query = update.pre_checkout_query
    if query.invoice_payload != 'Custom-Payload':
        context.bot.answer_pre_checkout_query(
            pre_checkout_query_id=query.id, ok=False,
            error_message="Something went wrong...")
        return
    context.bot.answer_pre_checkout_query(
        pre_checkout_query_id=query.id, ok=True
    )


def successful_payment_callback(
    update: Update, context: CallbackContext
) -> None:
    # do something after successful receive of payment?
    update.message.reply_text("Заказ оплачен! Спасибо!")


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
        'HANDLE_WAITING': handle_waiting,
        'HANDLE_DELIVERY': handle_delivery,
        'PAYMENT': start_with_shipping_callback,
        'SHIPPING_CALLBACK': shipping_callback,
    }
    state_handler = states_functions[user_state]
    try:
        logger.debug(f'Getting into {user_state}')
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        logger.error(err)


def main():
    load_dotenv()
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    token = os.getenv("PIZZA_SHOP_TG_BOTID")
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(
        MessageHandler(Filters.text | Filters.location, handle_users_reply))
    dispatcher.add_handler(
        CommandHandler('start', handle_users_reply, pass_job_queue=True),
    )
    dispatcher.add_handler(ShippingQueryHandler(shipping_callback))
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dispatcher.add_handler(MessageHandler(
        Filters.successful_payment, successful_payment_callback
    ))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
