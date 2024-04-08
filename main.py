import asyncio
import requests
import json

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart, Command
from datetime import datetime

from Token import TOKEN
from states import Authorization, Mileage
from keyboards.reply_inline import make_row_keyboard

dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def initialize(message: types.Message) -> None:
    await message.answer('Это бот для доступа к функциям автопарка из телеграмма. Ниже есть список доступных команд')


@dp.message(Command("login"))
async def authorize(message: types.Message, state: FSMContext) -> None:
    await state.set_state(Authorization.start)
    await message.answer('Пришлите логин и пароль в формате ЛОГИН:ПАРОЛЬ')


@dp.message(Authorization.start)
async def receive_credentials(message: types.Message, state: FSMContext) -> None:
    code = 0
    try:
        login, password = message.text.split(':')
        if not (login and password):
            raise ValueError

        url = 'https://localhost:7233/api/authorization/login'
        data = {'username': login, 'password': password}
        headers = {'Content-type': 'application/json'}

        response = requests.post(url, json=data, headers=headers, verify=False)
        code = response.status_code
        if code != 200:
            raise LookupError

        data = response.json()
        await state.update_data(token=data['token'])
        await message.answer(f'Добро пожаловать в систему, {login}')
    except ValueError:
        await message.answer('Не удалось прочитать данные пользователя, попробуйте ещё раз в формате ЛОГИН:ПАРОЛЬ')
    except LookupError:
        await message.answer(f'Не удалось провести авторизацию: код {code}')
    else:
        await state.set_state(Authorization.success)


@dp.message(Command("mileage"))
async def start_mileage(message: types.Message, state: FSMContext) -> None:
    await message.answer('Введите айди автомобиля, метраж которого вы хотите получить')
    await state.set_state(Mileage.start)


@dp.message(Mileage.start)
async def receive_mileage(message: types.Message, state: FSMContext) -> None:
    vehicle_id = message.text
    if not (vehicle_id and vehicle_id.isdigit()):
        await message.answer("Неверный формат айди автомобиля")
        return

    await state.update_data(vehicle_id=message.text)
    await state.set_state(Mileage.interval_input)
    await message.answer(
        text="Выберите интервал, за который выдать метраж выбранного автомобиля",
        reply_markup=make_row_keyboard(["День", "Месяц"])
    )


@dp.message(Mileage.interval_input)
async def input_interval(message: types.Message, state: FSMContext) -> None:
    intervals = {
        'ДЕНЬ': 'DAY',
        'МЕСЯЦ': 'MONTH',
        'DAY': 'DAY',
        'MONTH': 'MONTH',
    }

    translated_interval = intervals[message.text.upper()]

    if not translated_interval:
        await message.answer("Неправильный интервал")
        return

    await state.update_data(interval=translated_interval)
    await state.set_state(Mileage.dates_input)
    current_date = datetime.now()
    await message.answer(f'Введите даты, в которые должен входить метраж выбранного вами автомобиля в формате '
                         f'yyyy MM DD-yyyy MM DD (например, {current_date.year - 1} {current_date.month}'
                         f' {current_date.day}-{current_date.year} {current_date.month} {current_date.day})\nТакже вы '
                         f'можете дополнительно указать время в формате HH mm ss (например {current_date.hour} '
                         f'{current_date.minute} {current_date.second})')


@dp.message(Mileage.dates_input)
async def get_mileage(message: types.Message, state: FSMContext) -> None:
    first_date, second_date = message.text.strip().split('-')
    with_time = True
    try:
        start = datetime.strptime(first_date, '%Y %m %d %H %M %S')
        end = datetime.strptime(second_date, '%Y %m %d %H %M %S')
    except Exception as error:
        try:
            start = datetime.strptime(first_date, '%Y %m %d')
            end = datetime.strptime(second_date, '%Y %m %d')
        except Exception as error:
            await message.answer(f'Не вышло прочитать данные: {error}')
            raise error
        else:
            with_time = False

    try:
        token = (await state.get_data())['token']
        interval = (await state.get_data())['interval']
        vehicle_id = (await state.get_data())['vehicle_id']
        url = 'https://localhost:7233/api/reports/createvehiclesreport/' + vehicle_id + '/' + interval
        headers = {'Content-type': 'application/json', 'Authorization': f'Bearer {token}'}

        if with_time:
            parsed_start = start.strftime('%Y-%m-%dT%H:%M.%SZ')
            parsed_end = end.strftime('%Y-%m-%dT%H:%M.%SZ')
        else:
            parsed_start = start.strftime('%Y-%m-%dT00:00:00.000Z')
            parsed_end = end.strftime('%Y-%m-%dT00:00:00.000Z')

        data = json.dumps({"start": parsed_start, "end": parsed_end})

        response = requests.request("POST", url, data=data, headers=headers, verify=False)
        data = json.loads(response.text)

        text = ""
        for date, mileage in data.items():
            text += f"{date}: {mileage}\n"

        await message.answer(text)
    except Exception as e:
        await message.answer(f'An error occured while getting mileage: {e}')


async def main() -> None:
    bot = Bot(TOKEN, default=DefaultBotProperties())
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
