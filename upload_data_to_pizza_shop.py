import json
import logging
import os

import click
import requests
from dotenv import load_dotenv
from pytils.translit import slugify

from api_elasticpath import get_token

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def create_flow(url, access_token, name, description):
    headers = {'Authorization': access_token}
    json_data = {
        'data': {
            'type': 'flow',
            'name': name,
            'slug': slugify(name),
            'description': description,
            'enabled': True,
        },
    }
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json().get('data')


def create_field(url, access_token, name, field_type, description, flow):
    headers = {'Authorization': access_token}
    json_data = {
        'data': {
            'type': 'field',
            'name': name,
            'slug': slugify(name),
            'field_type': field_type,
            'description': description,
            'required': False,
            'enabled': True,
            'omit_null': False,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow,
                    },
                },
            },
        },
    }
    response = requests.post(url, headers=headers, json=json_data)
    response.raise_for_status()


@click.command()
@click.option(
    '--address',
    type=click.File('r', encoding='utf-8'),
    help='file with pizzeria addresses'
)
@click.option(
    '--menu',
    type=click.File('r', encoding='utf-8'),
    help='file with menu'
)
def main(address, menu):
    load_dotenv()
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    client_id = os.getenv('PIZZA_SHOP_CLIENT_ID')
    access_token = get_token(
        'https://api.moltin.com/oauth/access_token',
        client_id,
        client_secret=os.getenv('PIZZA_SHOP_CLIENT_SECRET', None)
    )
    if address:
        flow = create_flow(
            'https://api.moltin.com/v2/flows',
            access_token,
            'Pizzeria',
            'flow describing pizzeria'
        )
        flow_id = flow.get('id')
        fields = [
            ('Address', 'string', 'pizzeria-address'),
            ('Alias', 'string', 'pizzeria-name'),
            ('Longitude', 'string', 'longitude'),
            ('Latitude', 'string', 'latitude'),
            ('Delivery TG ID', 'string', 'delivery-id'),
        ]
        for field in fields:
            create_field(
                'https://api.moltin.com/v2/fields',
                access_token,
                *field,
                flow=flow_id
            )

        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        logger.debug(access_token)
        addresses = json.load(address)
        for address in addresses:
            json_data = {
                'type': 'entry',
                'address': address.get('address').get('full'),
                'alias': address.get('alias'),
                'longitude': address.get('coordinates').get('lon'),
                'latitude': address.get('coordinates').get('lat'),
                'delivery-tg-id': '451201167',
            }
            response = requests.post(
                'https://api.moltin.com/v2/flows/pizzeria/entries',
                headers=headers, json={'data': json_data}
            )
            response.raise_for_status()

    if menu:
        menu = json.load(menu)
        for item in menu:
            product = {
                'type': 'product',
                'name': item.get('name', None),
                'slug': slugify(f"{item.get('name')}-{item.get('id')}"),
                'sku': slugify(f"{item.get('name')}-{item.get('id')}"),
                'description': item.get('description'),
                'manage_stock': False,
                'price': [
                    {
                        'amount': item.get('price', None),
                        'currency': 'RUB',
                        'includes_tax': True
                    }
                ],
                'status': 'live',
                'commodity_type': 'physical',
            }
            response = requests.post(
                'https://api.moltin.com/v2/products',
                headers=headers,
                json={'data': product}
            )
            response.raise_for_status()
            shop_item = response.json().get('data')
            logger.debug(response.json())
            files = {
                'file_location': (None, item.get('product_image').get('url')),
            }

            response = requests.post(
                'https://api.moltin.com/v2/files',
                headers=headers,
                files=files
            )
            response.raise_for_status()
            shop_item_picture = response.json().get('data')
            logger.debug(response.json())

            shop_item_url = (
                f'https://api.moltin.com/v2/products/{shop_item.get("id")}'
                '/relationships/main-image'
            )
            json_data = {
                'data': {
                    'type': 'main_image',
                    'id': shop_item_picture.get('id'),
                },
            }
            response = requests.post(
                shop_item_url,
                headers=headers,
                json=json_data
            )
            response.raise_for_status()
            logger.debug(response.json())


if __name__ == '__main__':
    main()
