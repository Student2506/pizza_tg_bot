import os
from dataclasses import dataclass

import requests


@dataclass
class Address:
    latitude: float
    longitude: float


def fetch_coordinates(apikey, address):
    base_url = 'https://geocode-maps.yandex.ru/1.x'
    response = requests.get(base_url, params={
        'geocode': address,
        'apikey': apikey,
        'format': 'json',
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']
    found_places = found_places['featureMember']
    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(' ')
    return Address(latitude=lat, longitude=lon)


def main():
    yandex_api_key = os.getenv('PIZZA_SHOP_YA_TOKEN')
    coords = fetch_coordinates(yandex_api_key, 'Серпуховская')

    print(coords)


if __name__ == '__main__':
    main()
