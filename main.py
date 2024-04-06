import asyncio
import requests
import json

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart, Command

from Token import TOKEN
from states import Authorization

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

        response = requests.post(url, json=data, headers=headers)
        code = response.status_code
        if code != 200:
            raise LookupError

        data = json.loads(response.json())
        await state.update_data(token=data['token'])
        await message.answer(f'Добро пожаловать в систему, {data["username"]}')
    except ValueError:
        await message.answer('Не удалось прочитать данные пользователя, попробуйт ещё раз в формате ЛОГИН:ПАРОЛЬ')
    except LookupError:
        await message.answer(f'Не удалось провести авторизацию: код {code}')
    else:
        await state.set_state(Authorization.success)



async def main() -> None:
    bot = Bot(TOKEN, default=DefaultBotProperties())
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
