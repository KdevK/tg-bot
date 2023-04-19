async def weather_json_to_text(json_text):
    text = f'Температура: {int(json_text["main"]["temp"])} °C\n'
    text += f'Ощущается как: {int(json_text["main"]["feels_like"])} °C\n'
    text += f'Состояние: {json_text["weather"][0]["description"]}\n'
    text += f'Ветер: {json_text["wind"]["speed"]} м/c'
    return text

