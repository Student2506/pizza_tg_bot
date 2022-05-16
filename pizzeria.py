from geopy.distance import distance
from telegram import InlineKeyboardButton


def calculate_distance_and_price(pizzeria):
    message_to_customer = {
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
        message = message_to_customer['less_than_500_m']
        delivery_price = 0
        markup = [
            [InlineKeyboardButton('Доставка', callback_data='delivery'), ],
            [InlineKeyboardButton('Самовывоз', callback_data='pickup'), ]
        ]
        return message, markup, delivery_price

    if pizzeria.get('distance').m < 5000:
        message = message_to_customer['less_than_5_km']
        markup = [
            [InlineKeyboardButton('Доставка', callback_data='delivery'), ],
            [InlineKeyboardButton('Самовывоз', callback_data='pickup'), ]
        ]
        delivery_price = 100
        return message, markup, delivery_price

    if pizzeria.get('distance').m < 20000:
        message = message_to_customer['less_than_20_km']
        markup = [
            [InlineKeyboardButton('Доставка', callback_data='delivery'), ],
            [InlineKeyboardButton('Самовывоз', callback_data='pickup'), ]
        ]
        delivery_price = 300
        return message, markup, delivery_price

    message = message_to_customer['more_than_20_km']
    markup = [
        [InlineKeyboardButton('Самовывоз', callback_data='pickup'), ]
    ]
    delivery_price = 0
    return message, markup, delivery_price


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
            'pizzeria': pizzeria,
            'distance': pizza_distance,
        }
        pizzeria_distances.append(pizzeria_range)
    return min(pizzeria_distances, key=get_pizzeriza_range)
