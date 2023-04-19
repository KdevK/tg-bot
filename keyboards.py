from aiogram import types

default_kb = [
    [
        types.KeyboardButton(text="Погода"),
        types.KeyboardButton(text="Курс валют"),
    ],
    [
        types.KeyboardButton(text="Картинка с котиком", ),
        types.KeyboardButton(text="Создать опрос"), ],
]

default_keyboard = types.ReplyKeyboardMarkup(
    keyboard=default_kb,
    input_field_placeholder="Выберите функцию",
    row_width=2,
    resize_keyboard=True,
    one_time_keyboard=True,
)

cancel_kb = [[types.KeyboardButton(text="Отмена")]]

cancel_keyboard = types.ReplyKeyboardMarkup(
    keyboard=cancel_kb,
    resize_keyboard=True,
    one_time_keyboard=True,
)

anon_kb = [
    [types.KeyboardButton(text="Анонимный"), types.KeyboardButton(text="Публичный")]
]

anon_keyboard = types.ReplyKeyboardMarkup(
    keyboard=anon_kb,
    resize_keyboard=True,
    one_time_keyboard=True,
)
