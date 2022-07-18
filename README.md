# Проект телеграм-бота пиццерии
## Цель  
Создать бота с возможностью взаимодействовать с магазином Motlin (Elasticpath).  

## Технологии  
- Telegram  
- Python 3.9  
- Yandex Maps API  
- Redis  
- Elasticpath API
- Telegram Payment  
- Facebook  


## Инсталляция  
1. Создать окружение  
```
python -m venv venv  
source venv/bin/activate  
```
2. Установить зависимости  
```
python -m pip install --upgrade pip  
pip install -r requirements.txt  
```
3. Завести (создать) переменные среды окружения (токены):  

API Motlin  
- PIZZA_SHOP_CLIENT_ID=  
- PIZZA_SHOP_CLIENT_SECRET=  

База Redis  
- PIZZA_SHOP_DATABASE_HOST=  
- PIZZA_SHOP_DATABASE_PASSWORD=  
- PIZZA_SHOP_DATABASE_PORT=  

Токен Telegram  
- PIZZA_SHOP_TG_BOTID=  

Токен от банка для работы с Telegram Payment
- PIZZA_SHOP_PAY_TOKEN=  

Токен Yandex Карт
- PIZZA_SHOP_YA_TOKEN=  

Токены Facebook  
- PIZZA_SHOP_FB_TOKEN  
- PIZZA_SHOP_WEBHOOK_SHARED  

4. Создать товары
```
upload_data_to_pizza_shop.py --address address.json --menu menu.json
```
Образец меню пицц (menu.json)
```
[
	{
		"id": 20,
		"name": "Чизбургер-пицца",
		"description": "мясной соус болоньезе, моцарелла, лук, соленые огурчики, томаты, соус бургер",
		"food_value": {
			"fats": "6,9",
			"proteins": "7,5",
			"carbohydrates": "23,72",
			"kiloCalories": "188,6",
			"weight": "470±50"
		},
		"culture_name": "ru-RU",
		"product_image": {
			"url": "https://dodopizza-a.akamaihd.net/static/Img/Products/Pizza/ru-RU/1626f452-b56a-46a7-ba6e-c2c2c9707466.jpg",
			"height": 1875,
			"width": 1875
		},
		"price": 395
	},
```
Образец адресов (address.json)
```
[
    {
        "id": "00000351-0000-0000-0000-000000000000",
        "alias": "Афимолл",
        "address": {
            "full": "Москва, набережная Пресненская дом 2",
            "city": "Москва",
            "street": "Пресненская",
            "street_type": "набережная",
            "building": "2"
        },
        "coordinates": {
            "lat": "55.749299",
            "lon": "37.539644"
        }
    },
```

5. Запустить ботов  
```
python shop_bot_tg.py  
gunicorn --log-file=- app:app 
```

[Пример бота](https://t.me/pizzeria_student83_bot)  
 