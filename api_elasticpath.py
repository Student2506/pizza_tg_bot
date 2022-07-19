import datetime
import logging
import urllib.parse

import requests

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

SITE_TOKEN_LIFETIME = None
SITE_TOKEN = None
SITE_CLIENT_TOKEN = None
SITE_CLIENT_TOKEN_LIFETIME = None


def get_token(url, client_id, client_secret=None):
    global SITE_TOKEN, SITE_TOKEN_LIFETIME, SITE_CLIENT_TOKEN
    global SITE_CLIENT_TOKEN_LIFETIME

    now = datetime.datetime.now()
    if not client_secret and SITE_TOKEN_LIFETIME:
        logger.debug(
            f'Time is now: {now} and token valid until: '
            f'{datetime.datetime.fromtimestamp(SITE_TOKEN_LIFETIME)}'
        )
    if client_secret and SITE_CLIENT_TOKEN_LIFETIME:
        logger.debug(
            f'Time is now: {now} and token valid until: '
            f'{datetime.datetime.fromtimestamp(SITE_CLIENT_TOKEN_LIFETIME)}'
        )
    if not client_secret and SITE_TOKEN and (
        SITE_TOKEN_LIFETIME > datetime.datetime.timestamp(now)
    ):
        logger.debug(f'Getting old token {SITE_TOKEN}')
        return SITE_TOKEN
    elif not client_secret:
        logger.debug('Requesting new token')
        logger.debug(f'Old token: {SITE_TOKEN}')
        data = {
            'client_id': client_id,
            'grant_type': 'implicit'
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        token = response.json()
        SITE_TOKEN_LIFETIME = token.get('expires')
        SITE_TOKEN = token.get('access_token')
        logger.debug(f'New token: {SITE_TOKEN}')
        return SITE_TOKEN

    if client_secret and SITE_CLIENT_TOKEN and (
        SITE_CLIENT_TOKEN_LIFETIME > datetime.datetime.timestamp(now)
    ):
        logger.debug(f'Getting old token {SITE_CLIENT_TOKEN}')
        return SITE_CLIENT_TOKEN
    else:
        logger.debug('Requesting new token')
        logger.debug(f'Old token: {SITE_CLIENT_TOKEN}')
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        token = response.json()
        SITE_CLIENT_TOKEN_LIFETIME = token.get('expires')
        SITE_CLIENT_TOKEN = token.get('access_token')
        logger.debug(f'New token: {SITE_CLIENT_TOKEN}')
        return SITE_CLIENT_TOKEN


def get_catalog(url, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_product_detail(url, product_id, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'{url}{product_id}/', headers=headers)
    response.raise_for_status()
    return response.json().get('data')


def get_product_picture_url(url, picture_id, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(
        f'{url}{picture_id}', headers=headers
    )
    response.raise_for_status()
    return response.json().get('data').get('link').get('href')


def get_cart(url, access_token, client_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'{url}{client_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def add_proudct_to_cart(url, product_id, quantity, access_token, client_id):
    logger.debug(
        f'{url}, {product_id}, {quantity}, {access_token}, {client_id}'
    )
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-MOLTIN-CURRENCY': 'RUB',
    }
    json_data = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': quantity,
        }
    }
    logger.debug(json_data)
    response = requests.post(
        f'{url}{client_id}/items', headers=headers, json=json_data
    )
    response.raise_for_status()
    return response.json()


def remove_products_from_cart(url, cart_product_id, access_token, client_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.delete(
        f'{url}{client_id}/items/{cart_product_id}', headers=headers
    )
    response.raise_for_status()
    return response.json()


def get_cart_products(url, access_token, client_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'{url}{client_id}/items', headers=headers)
    response.raise_for_status()
    return response.json()


def get_pizzeries_coordinates(url, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get('data')


def create_customer_address(url, access_token, location):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    json_data = {
        'data': {
            'type': 'entry',
            'longitude': location.longitude,
            'latitude': location.latitude,
        }
    }
    logger.debug(json_data)
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json().get('data').get('id')


def get_customer_address(url, access_token, id):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.get(f'{url}/{id}', headers=headers)
    response.raise_for_status()
    return response.json().get('data')


def get_products_by_category_id(url, access_token, id):
    filter_string = urllib.parse.quote_plus(f'eq(category.id,{id})')
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    params = {
        'filter': filter_string,
    }
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    products = response.json().get('data')
    logger.debug(products)
    return products


def get_products_by_category_slug(url, access_token, slug):
    filter_string = urllib.parse.quote_plus(f'eq(slug,{slug})')
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    params = {
        'filter': filter_string,
    }
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    products = response.json().get('data')
    logger.debug(products)
    return products
