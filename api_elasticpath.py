import datetime
import logging

import requests

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

SITE_TOKEN_LIFETIME = None
SITE_TOKEN = None


def get_token(url, client_id, client_secret=None):
    global SITE_TOKEN
    global SITE_TOKEN_LIFETIME
    now = datetime.datetime.now()
    if SITE_TOKEN and SITE_TOKEN_LIFETIME < datetime.datetime.timestamp(now):
        return SITE_TOKEN
    else:
        if client_secret is None:
            data = {
                'client_id': client_id,
                'grant_type': 'implicit'
            }
        else:
            data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'client_credentials'
            }
        response = requests.post(url, data=data)
        response.raise_for_status()
        token = response.json()
        SITE_TOKEN_LIFETIME = token.get('expires')
        SITE_TOKEN = token.get('access_token')

    return SITE_TOKEN


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


def get_fish_picture_url(url, picture_id, access_token):
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


def create_customer_record(url, access_token, user, email):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    json_data = {
        'data': {
            'type': 'customer',
            'name': user,
            'email': email,
        }
    }
    logger.debug(json_data)
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()
