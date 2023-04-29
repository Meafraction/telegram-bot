import os

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.utils.markdown import hlink, hbold
from aiogram.dispatcher import FSMContext

# from dotenv import load_dotenv

from main import get_all_drugs, get_drug, get_number_drug, get_list_drug, get_more_info

PROXY_URL = "http://proxy.server:3128"
bot = Bot(token=os.environ.get('TOKEN'), parse_mode=types.ParseMode.HTML, proxy=PROXY_URL)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

type_drug, id_drug, shop_dict, loc = None, None, None, None
STATE_ENTER_TEXT = 'enter_text'


@dp.message_handler(commands=["start"])
async def start_command_handler(message: types.Message):
    message_text = "Привет! Я бот-поисковик лекарств. Что бы вы хотели найти?"
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True) \
        .add(KeyboardButton("Поиск"), KeyboardButton("Местоположение", request_location=True))
    await bot.send_message(chat_id=message.chat.id, text=message_text, reply_markup=keyboard)


@dp.message_handler(content_types=types.ContentType.LOCATION)
async def handler_location(message: types.Message):
    global loc
    loc = message.location


@dp.message_handler(Text('Поиск'))
async def search_handler(message: types.Message, state: FSMContext):
    message_text = "Введите ваш запрос для поиска:"
    await bot.send_message(chat_id=message.chat.id, text=message_text)
    await state.set_state(STATE_ENTER_TEXT)


@dp.message_handler(state=STATE_ENTER_TEXT)
async def text_message_handler(message: types.Message, state: FSMContext):
    drugs_dict = get_all_drugs(url="https://apteka.103.by/lekarstva-brest-region/")
    ru_drug = message.text
    drugs = {}
    i = 1
    for key, value in drugs_dict.items():
        if ru_drug.lower() in key.lower():
            drugs[i] = value
            i += 1
    if drugs:
        keyboard = InlineKeyboardMarkup()
        for k, v in drugs.items():
            drug_button = InlineKeyboardButton(text=v, callback_data=f"drug_{v}")
            keyboard.add(drug_button)
        message_text = "Выберите нужный препарат:"
        await state.finish()
        await bot.send_message(chat_id=message.chat.id, text=message_text, reply_markup=keyboard)
    else:
        message_text = "К сожалению, по вашему запросу ничего не найдено."
        await state.finish()
        await bot.send_message(chat_id=message.chat.id, text=message_text)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('drug_'))
async def process_drug_callback(callback_query: types.CallbackQuery):
    global type_drug
    drug_name = callback_query.data.split('_')[1]
    drug_dict = get_drug(url=f'https://apteka.103.by/{drug_name}/brest/', drug=drug_name)

    if drug_dict:
        keyboard = InlineKeyboardMarkup()
        for k, v in drug_dict.items():
            drug_button = InlineKeyboardButton(text=v, callback_data=f"type_{v}")
            keyboard.add(drug_button)
        message_text = "Выберите нужный препарат:"
        await bot.send_message(chat_id=callback_query.message.chat.id, text=message_text, reply_markup=keyboard)
    else:
        message_text = "К сожалению, по вашему запросу ничего не найдено."
        await bot.send_message(chat_id=callback_query.message.chat.id, text=message_text)

    type_drug = drug_name


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('type_'))
async def process_type_callback(callback_query: types.CallbackQuery):
    global type_drug, id_drug, shop_dict
    drug_name = callback_query.data.split('_')[1]

    id_drug = get_number_drug(url=f"https://apteka.103.by/{type_drug}/{drug_name}/brest/")
    shop_dict = get_list_drug(url=f'https://apteka.103.by/api/v2/pharmacy/map/33/{id_drug}/')

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("По цене(10 шт.)", callback_data="price"),
        InlineKeyboardButton("По месту(10 шт.)", callback_data="location", request_location=True))
    await bot.send_message(chat_id=callback_query.from_user.id, text='Выберите желаемый поиск', reply_markup=keyboard)


@dp.callback_query_handler(text='price')
async def price_callback(callback_query: types.CallbackQuery):
    global id_drug, shop_dict
    shop_dict = sorted(shop_dict, key=lambda x: x[1])
    result = get_more_info(shop_dict=shop_dict[:10], id_drug=id_drug, loc=loc)
    for item in result:
        address = f'https://yandex.ru/maps/?text={item.get("address")}'
        card = f'{hbold("Название: ")}{item.get("name")}\n' \
               f'{hbold("Цена: ")}{item.get("price")}\n' \
               f'{hbold("Адрес: ")}{hlink(item.get("address"), address)}\n' \
               f'{hbold("Телефон: ")}{item.get("phone")}\n'
        await bot.send_message(chat_id=callback_query.from_user.id, text=card)


@dp.callback_query_handler(text='location')
async def location_callback(callback_query: types.CallbackQuery):
    global id_drug, shop_dict
    result = get_more_info(shop_dict=shop_dict, id_drug=id_drug, loc=loc)
    result = sorted(result, key=lambda x: x["distance"])[:10]

    for item in result:
        address = f'https://yandex.ru/maps/?text={item.get("address")}'
        card = f'{hbold("Название: ")}{item.get("name")}\n' \
               f'{hbold("Цена: ")}{item.get("price")}\n' \
               f'{hbold("Адрес: ")}{hlink(item.get("address"), address)}\n' \
               f'{hbold("Телефон: ")}{item.get("phone")}\n'
        await bot.send_message(chat_id=callback_query.from_user.id, text=card)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
