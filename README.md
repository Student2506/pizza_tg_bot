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

4. Создать товары
```
upload_data_to_pizza_shop.py --address address.json --menu menu.json
```
 ![Образец меню пицц](/menu_json.png)
 ![Образец адрсов](/address_json.png)


5. Запустить бота  
```
python shop_bot_tg.py  
```

[Пример бота](https://t.me/pizzeria_student83_bot)  
 