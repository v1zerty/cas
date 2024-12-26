import logging
import random
import string
import time
from typing import Any, List, Optional, Union

import requests
from aiocryptopay.const import Assets, HTTPMethods
from aiocryptopay import AioCryptoPay as _AioCryptoPay, Networks
from aiogram import Bot, Dispatcher, executor, types
from pydantic import ValidationError

import config2 as config

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)


class AioCryptoPay(_AioCryptoPay):
    async def create_invoice_json(
        self,
        amount: Union[int, float],
        asset: Optional[Union[Assets, str]] = None,
        # description: Optional[str] = None,
        # hidden_message: Optional[str] = None,
        # paid_btn_name: Optional[Union[PaidButtons, str]] = None,
        # paid_btn_url: Optional[str] = None,
        # payload: Optional[str] = None,
        # allow_comments: Optional[bool] = None,
        # allow_anonymous: Optional[bool] = None,
        # expires_in: Optional[int] = None,
        # fiat: Optional[str] = None,
        # currency_type: Optional[Union[CurrencyType, str]] = None,
        # accepted_assets: Optional[Union[List[Union[Assets, str]], str]] = None,
    ) -> dict[str, Any]:
        method = HTTPMethods.GET
        url = f"{self.network}/api/createInvoice"

        # if accepted_assets and type(accepted_assets) == list:
        #    accepted_assets = ",".join(map(str, accepted_assets))

        params = {
            "asset": asset,
            "amount": amount,
            # "description": description,
            # "hidden_message": hidden_message,
            # "paid_btn_name": paid_btn_name,
            # "paid_btn_url": paid_btn_url,
            # "payload": payload,
            # "allow_comments": allow_comments,
            # "allow_anonymous": allow_anonymous,
            # "expires_in": expires_in,
            # "fiat": fiat,
            # "currency_type": currency_type,
            # "accepted_assets": accepted_assets,
        }

        for key, value in params.copy().items():
            if isinstance(value, bool):
                params[key] = str(value).lower()
            if value is None:
                del params[key]

        response = await self._make_request(
            method=method, url=url, params=params, headers=self.__headers
        )
        return response["result"]


cryptopay = AioCryptoPay(config.CRYPTO_TOKEN, network="https://testnet-pay.crypt.bot")


async def pay_money(amount, id):
    try:
        payme = await cryptopay.create_check(asset="USDT", amount=amount)
        keyboard = types.InlineKeyboardMarkup()
        prize = types.InlineKeyboardButton(text="🎁", url=payme.bot_check_url)
        keyboard.add(prize)
        await bot.send_message(
            id,
            f"<b>[💸] Выплата:\n</b>\n<blockquote><b>Сумма: {amount}$</b></blockquote>",
            reply_markup=keyboard,
        )
    except Exception as e:
        await bot.send_message(
            id,
            f"<b>[⛔] Ошибка..., прасти браток денег в казне нет</b>\nНе удалось выплатить <b>{amount}</b>!\nНапишите @ThisFataew за выплатой",
        )
        for admid in config.ADMIN_IDS:
            await bot.send_message(
                admid,
                f"<b>ДАЛБОЕБ ПОПОЛНИ КАЗНУ НАХУЙ!</b>\nБот не может создать выплату!\n\nЮзер: {id}\nСумма: {amount}\n\nЛог ошибки: <b>{e}</b>",
            )


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply("[👋] Привет!  Спасибо что выбрали нас💚!")


@dp.channel_post_handler(chat_id=config.PAY_ID)
async def handle_new_bet(message: types.Message):
    try:
        bet_usd = message.text.split("($")[1].split(").")[0]
        bet_usd = float(bet_usd.replace(",", ""))
        bet_coment = message.text.split("💬 ")[1]
        bet_comment = bet_coment.lower()
        player_name = message.text.split("отправил(а)")[0].strip()
        user = message.entities[0].user
        player_id = user.id
        keyboard = types.InlineKeyboardMarkup()
        url_button = types.InlineKeyboardButton(
            text="Сделать ставку", url=config.pinned_link
        )
        keyboard.add(url_button)
        bet_design = config.bet.format(
            bet_usd=bet_usd, player_name=player_name, bet_comment=bet_comment
        )
        await bot.send_photo(
            chat_id=config.MAIN_ID,
            photo=open("img/new_bet.png", "rb"),
            caption=bet_design,
            reply_markup=keyboard,
        )
        if bet_comment.startswith("куб"):
            if bet_comment in config.ag_dice:
                await handle_dice(message, bet_usd, bet_comment, player_id)
            else:
                await bot.send_message(
                    config.MAIN_ID,
                    "<blockquote><b>💬 | Вы указали неверную игру!\n\n📌 | Для получения средств обратно, напишите ТС-у из описания канала.</b></blockquote>",
                )
        else:
            await bot.send_message(
                config.MAIN_ID,
                "<blockquote><b>💬 | Вы указали неверную игру!\n\n📌 | Для получения средств обратно, напишите ТС-у из описания канала.</b></blockquote>",
            )
    except IndexError:
        player_name = message.text.split("отправил(а)")[0].strip()
        await bot.send_message(
            config.MAIN_ID,
            f"<b>[⛔] Ошибка!</b>\n\n<blockquote><b>Игрок {player_name} не указал комментарий!\nНапишите администратору @ThisFataew за возвратом (-20% от ставки)!</b></blockquote>",
        )
    except AttributeError as e:
        player_name = message.text.split("отправил(а)")[0].strip()
        await bot.send_message(
            config.MAIN_ID,
            f"<b>[⛔] Ошибка!</b>\n\n<blockquote><b>Не удалось распознать игрока {player_name}!\nНапишите администратору @ThisFataew за возвратом</b></blockquote>",
        )
    except Exception:
        await bot.send_message(
            config.MAIN_ID,
            "<b>[⛔] Произошла неизвестная ошибка при обработке ставки!</b>",
        )


async def handle_dice(message, bet_usd, bet_comment, player_id):
    dice_value = await bot.send_dice(chat_id=config.MAIN_ID)
    dice_value = dice_value.dice.value

    bet_type = bet_comment.split(" ")[1].lower()

    if bet_type == "меньше":
        if dice_value in [1, 2, 3]:
            win_amount = bet_usd * config.cef
            try:
                await pay_money(win_amount, player_id)
                await bot.send_photo(
                    chat_id=config.MAIN_ID,
                    photo=open("img/win.png", "rb"),
                    caption=f"<b>🎉 Поздравляем, вы выиграли   {win_amount}$!</b>\n\n<blockquote><b>🚀 Ваш выигрыш успешно отправлен чеком боту https://t.me/CasinoFataewBot</b></blockquote>",
                )
            except Exception as e:
                logging.error(f"Ошибка при выплате: {e}")
                await bot.send_photo(
                    chat_id=config.MAIN_ID,
                    photo=open("img/win.png", "rb"),
                    caption=f"<blockquote><b>🎉 Поздравляем, вы выиграли {win_amount}, но вы не зарегистрированы в боте: https://t.me/CasinoFataewBot. Напишите в ЛС одному из ТСОВ!</b></blockquote>",
                )
        else:
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open("img/lose.png", "rb"),
                caption="<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>",
            )
    elif bet_type == "больше":
        if dice_value in [4, 5, 6]:
            win_amount = bet_usd * config.cef
            try:
                await pay_money(win_amount, player_id)
                await bot.send_photo(
                    chat_id=config.MAIN_ID,
                    photo=open("img/win.png", "rb"),
                    caption=f"<b>🎉 Поздравляем, вы выиграли   {win_amount}$!</b>\n\n<blockquote><b>🚀 Ваш выигрыш успешно отправлен чеком боту https://t.me/CasinoFataewBot</b></blockquote>",
                )
            except Exception as e:
                logging.error(f"Ошибка при выплате: {e}")
                await bot.send_photo(
                    chat_id=config.MAIN_ID,
                    photo=open("img/win.png", "rb"),
                    caption=f"<blockquote><b>🎉 Поздравляем, вы выиграли {win_amount}, но вы не зарегистрированы в боте: https://t.me/CasinoFataewBot. Напишите в ЛС одному из ТСОВ!</b></blockquote>",
                )
        else:
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open("img/lose.png", "rb"),
                caption="<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>",
            )
    elif bet_type in ["чет", "четное", "чёт"]:
        if dice_value in [2, 4, 6]:
            win_amount = bet_usd * config.cef
            try:
                await pay_money(win_amount, player_id)
                await bot.send_photo(
                    chat_id=config.MAIN_ID,
                    photo=open("img/win.png", "rb"),
                    caption=f"<b>🎉 Поздравляем, вы выиграли   {win_amount}$!</b>\n\n<blockquote><b>🚀 Ваш выигрыш успешно отправлен чеком боту https://t.me/CasinoFataewBot</b></blockquote>",
                )
            except Exception as e:
                logging.error(f"Ошибка при выплате: {e}")
                await bot.send_photo(
                    chat_id=config.MAIN_ID,
                    photo=open("img/win.png", "rb"),
                    caption=f"<blockquote><b>🎉 Поздравляем, вы выиграли {win_amount}, но вы не зарегистрированы в боте: https://t.me/CasinoFataewBot. Напишите в ЛС одному из ТСОВ!</b></blockquote>",
                )
        else:
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open("img/lose.png", "rb"),
                caption="<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>",
            )
    elif bet_type in ["нечет", "нечетное", "нечётное"]:
        if dice_value in [1, 3, 5]:
            win_amount = bet_usd * config.cef
            try:
                await pay_money(win_amount, player_id)
                await bot.send_photo(
                    chat_id=config.MAIN_ID,
                    photo=open("img/win.png", "rb"),
                    caption=f"<b>🎉 Поздравляем, вы выиграли   {win_amount}$!</b>\n\n<blockquote><b>🚀 Ваш выигрыш успешно отправлен чеком боту https://t.me/CasinoFataewBot</b></blockquote>",
                )
            except Exception as e:
                logging.error(f"Ошибка при выплате: {e}")
                await bot.send_photo(
                    chat_id=config.MAIN_ID,
                    photo=open("img/win.png", "rb"),
                    caption=f"<blockquote><b>🎉 Поздравляем, вы выиграли {win_amount}, но вы не зарегистрированы в боте: https://t.me/CasinoFataewBot. Напишите в ЛС одному из ТСОВ!</b></blockquote>",
                )
        else:
            await bot.send_photo(
                chat_id=config.MAIN_ID,
                photo=open("img/lose.png", "rb"),
                caption="<blockquote><b>❌ | К сожалению, вы проиграли.</b></blockquote>",
            )
    else:
        await bot.send_message(
            config.MAIN_ID,
            "<blockquote><b>💬 | Вы указали неверную игру!\n\n📌 | Для получения средств обратно, напишите ТС-у из описания канала.</b></blockquote>",
        )


@dp.message_handler(commands=["create_invoice"])
async def create_invoice(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply(
            "<b>[⛔] Ошибка!</b>\n\n<blockquote>Вы не являетесь администратором!</blockquote>"
        )
        return

    try:
        amount = float(message.text.split()[1])
        invoice = await cryptopay.create_invoice_json(asset="USDT", amount=amount)

        payment_url = (
            invoice.get("pay_url")
            or invoice.get("bot_invoice_url")
            or f"https://pay.crypt.bot/{invoice.get('invoice_id')}"
        )
        # Проверяем наличие атрибута pay_url
        # if hasattr(invoice, 'pay_url'):
        #    payment_url = invoice.pay_url
        # elif hasattr(invoice, 'bot_invoice_url'):
        #    payment_url = invoice.bot_invoice_url
        # else:
        #    Если нет ни pay_url, ни bot_invoice_url, используем ID инвойса
        #    payment_url = f"https://pay.crypt.bot/{invoice.invoice_id}"

        keyboard = types.InlineKeyboardMarkup()
        pay_button = types.InlineKeyboardButton(text="Оплатить", url=payment_url)
        keyboard.add(pay_button)

        await message.reply(
            f"Создан счет для пополнения казны на сумму {amount} USDT:\n"
            f"ID инвойса: {invoice['invoice_id']}\n"
            f"Статус: {invoice['status']}\n"
            f"Для оплаты нажмите кнопку ниже:",
            reply_markup=keyboard,
        )

    except ValidationError as ver:
        logging.error(repr(ver.errors()[0]))

    except Exception as e:
        logging.error(f"Ошибка при создании инвойса: {str(e)}", exc_info=True)
        await message.reply(f"Произошла ошибка при создании счета: {str(e)}")
        raise e


@dp.message_handler(commands=["del_checks"])
async def delete_all_invoices(message: types.Message):
    checks = await cryptopay.get_checks(status="active")
    if message.from_user.id in config.ADMIN_IDS:
        await message.reply(checks)
    else:
        await message.reply(
            "<b>[⛔] Ошибка!</b>\n\n<blockquote>Вы не являетесь администратором!</blockquote>"
        )


@dp.message_handler(commands=["delete_check"])
async def delete_check(message: types.Message):
    if message.from_user.id in config.ADMIN_IDS:
        check_id = message.text.split("/delete_check ")
        await cryptopay.delete_check(check_id[1])
        await message.answer("Чек удалены")
    else:
        await message.reply(
            "<b>[⛔] Ошибка!</b>\n\n<blockquote>Вы не являетесь администратором!</blockquote>"
        )


@dp.message_handler(commands=["balance"])
async def check_balance(message: types.Message):
    if message.from_user.id in config.ADMIN_IDS:
        balance = await cryptopay.get_balance()
        await message.answer(balance)
    else:
        message.reply("пошел нахуй малыш")


@dp.message_handler(commands=["pay_money"])
async def cmd_paymoney(message: types.Message):
    if message.from_user.id in config.ADMIN_IDS:
        amount = float(message.text.split(" ")[2])
        id = int(message.text.split(" ")[1])
        await pay_money(amount, id)
        await message.reply("Средства успешно переведены")
    else:
        await message.reply(
            "<b>[⛔] Ошибка!</b>\n\n<blockquote>Вы не являетесь администратором!</blockquote>"
        )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
