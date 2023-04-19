import logging
import aiohttp
import aiofiles
import time
import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from aiogram.types import InputFile, ReplyKeyboardRemove
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from services.weather import weather_json_to_text
from services.currency import get_acronyms
from keyboards import default_keyboard, anon_keyboard

from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.environ.get("API_TOKEN")
WEATHER_TOKEN = os.environ.get("WEATHER_TOKEN")
CURRENCY_TOKEN = os.environ.get("CURRENCY_TOKEN")

# Конфигурация логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота, хранилища и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class UserState(StatesGroup):
    """
    Класс предоставляет 5 состояний, от которых зависит поведение бота
    - weather для обработки запросов прогноза погоды
    - currency для обработки запросов конвертации валют
    - poll_anon для обработки указания типа голосования: публичный или анонимный
    - poll_topic для обработки указания названия голосования
    - poll_options для обработки вариантов ответа
    """
    weather = State()
    currency = State()
    poll_anon = State()
    poll_topic = State()
    poll_options = State()


@dp.message_handler(commands=["cancel"], state=UserState.all_states)
async def cancel(message: types.Message, state: FSMContext):
    """
    Метод используется для отмены текущей операции, отменяя текущее состояние
    :param message:
    :param state:
    :return:
    """
    await state.finish()
    await message.answer("Вы отменили операцию")
    await message.answer("Какой функцией бота вы хотите воспользоваться?", reply_markup=default_keyboard)


@dp.message_handler(commands=["state"], state="*")
async def check_state(message: types.Message, state: FSMContext):
    """
    Метод используется для определения текущего состояния бота для дебага
    :param message:
    :param state:
    :return:
    """
    state_name = await state.get_state()
    if state_name is None:
        state_name = "Без состояния"
    await message.answer(state_name)


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message, state: FSMContext):
    """
    Метод используется для отправки приветственного меню
    :param message:
    :param state:
    :return:
    """
    await state.finish()
    await message.answer("Какой функцией бота вы хотите воспользоваться?", reply_markup=default_keyboard)


@dp.message_handler(Text(equals="Картинка с котиком", ignore_case=True))
async def send_cat(message: types.Message):
    """
    Метод используется для загрузки, сохранения и отправки случайной картинки с кошками
    :param message:
    :return:
    """
    time_now = time.time()
    user_id = message.from_user.id
    path = f"static/{user_id}_{time_now}.png"
    url = "https://cataas.com/cat"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(path, mode='wb')
                await f.write(await resp.read())
                await f.close()
    try:
        photo = InputFile(path)
        await bot.send_photo(message.chat.id, photo=photo, reply_markup=default_keyboard)
    except BaseException:
        await message.answer("Простите, сервер с котиками отвалился", reply_markup=default_keyboard)


@dp.message_handler(Text(equals="Погода", ignore_case=True))
async def send_weather(message: types.Message, state: FSMContext):
    """
    Метод используется, чтобы привести бота в состояние weather, чтобы дальнейшее сообщение пользователя
    регистрировалось как город, для которого требуется сделать запрос на прогноз погоды
    :param message:
    :param state:
    :return:
    """
    await message.answer("Для отмены операции нажмите на шторку около поля ввода и выберите /cancel")
    await message.answer("Введите ваш город")
    await UserState.weather.set()


@dp.message_handler(state=UserState.weather)
async def process_weather_state(message: types.Message, state: FSMContext):
    """
    Метод используется, чтобы в состоянии weather обработать сообщение пользователя, в котором он отправит нужный город,
    и в ответ отправить погоду
    :param message:
    :param state:
    :return:
    """
    url = f"https://api.openweathermap.org/data/2.5/weather?q={message.text}&appid={WEATHER_TOKEN}&lang=ru&units=metric"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                response = await resp.json()
                refined_response = await weather_json_to_text(response)
                await state.finish()
                await message.answer(refined_response, reply_markup=default_keyboard)
            else:
                refined_response = "Не удалось найти данные. Возможно, вы неверно указали название города...\n" \
                                   "Попробуйте снова"
                await message.answer(refined_response)


@dp.message_handler(commands=["codes"], state="*")
async def get_codes(message: types.Message, state: FSMContext):
    await message.answer(await get_acronyms())


@dp.message_handler(Text(equals="Курс валют", ignore_case=True))
async def send_currency(message: types.Message):
    """
    Метод используется, чтобы привести бота в состояние currency, чтобы дальнейшее сообщение пользователя
    регистрировалось как запрос на конвертацию
    :param message:
    :return:
    """
    await UserState.currency.set()
    await message.answer("Для отмены операции нажмите на шторку около поля ввода и выберите /cancel")
    await message.answer("Пожалуйста, введите строку в формате:\n<Из> <Количество> <В>\nНапример: RUB 5000 USD\n"
                         "Со списком кодов валют вы можете ознакомиться с помощью команды /codes")


@dp.message_handler(state=UserState.currency)
async def process_currency_state(message: types.Message, state: FSMContext):
    """
    Метод используется, чтобы в состоянии currency обработать сообщение пользователя, в котором он отправит строку
    по образцу, сделать запрос на API сервиса по конвертации и выдать результат пользователю
    :param message:
    :param state:
    :return:
    """
    try:
        cur_from, amount, cur_to = message.text.split(" ")
        url = f"https://api.api-ninjas.com/v1/convertcurrency?want={cur_to}&have={cur_from}&amount={amount}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    refined_response = f"Из {amount} {cur_from} вы получите {response['new_amount']} {cur_to}"
                    await state.finish()
                    await message.answer(refined_response, reply_markup=default_keyboard)
                else:
                    refined_response = "Конвертация не удалась. Возможно, вы неверно указали коды валют...\n" \
                                       "Попробуйте снова"
                    await message.answer(refined_response)
    except BaseException:
        await message.answer("Конвертация не удалась. Возможно, вы указали строку в неверном формате...\n"
                             "Попробуйте снова")


@dp.message_handler(Text(equals="Создать опрос", ignore_case=True))
async def send_poll(message: types.Message):
    """
    Метод используется, чтобы предложить пользователю создать опрос и привести бота в состояние, когда следующее
    сообщение будет определять тип опроса
    :param message:
    :return:
    """
    await UserState.poll_anon.set()
    await message.answer("Для отмены операции нажмите на шторку около поля ввода и выберите /cancel")
    await message.answer("Выберите тип опроса", reply_markup=anon_keyboard)


@dp.message_handler(state=UserState.poll_anon)
async def process_poll_anon_state(message: types.Message, state: FSMContext):
    """
    Метод используется, чтобы определить тип опроса и привести бота в состояние, когда следующее сообщение будет
    определять заголовок опроса
    :param message:
    :param state:
    :return:
    """
    if message.text.upper() in ["АНОНИМНЫЙ", "ПУБЛИЧНЫЙ"]:
        is_anonymous = True if message.text.upper() == "АНОНИМНЫЙ" else False
        await state.update_data(is_anonymous=is_anonymous)
        await UserState.poll_topic.set()
        await message.answer("Выберите заголовок опроса", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Неверно указан тип опроса, попробуйте снова")


@dp.message_handler(state=UserState.poll_topic)
async def process_poll_topic_state(message: types.Message, state: FSMContext):
    """
    Метод используется, чтобы определить заголовок опроса и привести бота в состояние, когда следующее сообщение будет
    определять варианты ответа
    :param message:
    :param state:
    :return:
    """
    if message.text:
        await state.update_data(topic=message.text)
        await UserState.poll_options.set()
        await message.answer("Укажите варианты ответа: каждый вариант на новой строке")
    else:
        await message.answer("Неправильно указано название опроса, попробуйте снова")


@dp.message_handler(state=UserState.poll_options)
async def process_poll_topic_state(message: types.Message, state: FSMContext):
    """
    Метод используется, чтобы определить варианты ответа и выдать готовый опрос
    :param message:
    :param state:
    :return:
    """
    if len(message.text.split("\n")) >= 2:
        options = message.text.split("\n")
        user_data = await state.get_data()
        await message.answer("Готово! Теперь вы можете переслать этот опрос!")
        await message.answer_poll(question=user_data["topic"], options=options, is_anonymous=user_data["is_anonymous"],
                                  reply_markup=default_keyboard)
        await state.finish()
        await state.reset_data()
    else:
        await message.answer("Неправильно указаны варианты ответа, попробуйте снова")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
