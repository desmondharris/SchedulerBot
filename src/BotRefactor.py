import datetime
import logging
import os
import asyncio

from dotenv import load_dotenv

import peewee

import telegram
from telegram import ForceReply, Update, Message, MessageEntity, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, \
    CallbackQueryHandler

from .BotSQL import Chat, RecurringEvent, NonRecurringEvent
from .MessageOptions import *
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

load_dotenv()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Message:
    """
    @param update: update.message != none
    @param context: unused
    @return: none
    """
    chat_id = update.effective_chat.id

    chat_model, created = Chat.get_or_create(id=chat_id)
    # get or create can cause integrity error if chat with id already exists, but exact params were not given. edge case
    # https://stackoverflow.com/questions/19362085/get-or-create-throws-integrity-error

    logger.debug(chat_model, created)
    if created:
        return await update.get_bot().send_message(update.message.chat_id, FIRST_TIME_GREETING)
    else:
        return await update.get_bot().send_message(update.message.chat_id, START_HELP_MESSAGE)


async def onetime_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Message:
    """
    Entry point for creating a one-time event
    @param update: update.message != none
    @param context: unused
    @return: none
    """
    info = update.message.text

    months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
              "november", "december"]
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    if info.split()[1].lower() in months:
        pass
    elif info.split()[1].lower() in days:
        _, weekday, time, event_name = info.split(maxsplit=3)
        logger.debug((weekday, time, event_name))
        res = await update.message.reply_text(WEEKDAY_INLINE_TEXT, reply_markup=WEEKDAY_INLINE_KB)
        NonRecurringEvent.create(
            user=update.effective_chat.id,
            name=event_name,
            date=datetime.date.today(),
            time=datetime.datetime.strptime(time, "%H%M").time(),
            reminders="",
            reminder_open = True
        )
        return res
    else:
        logger.warning(f"User {update.effective_user} in chat {update.effective_chat} attempted invalid ote")
        await update.message.reply_text("Please input a one-time event in one of the proper formats!")


async def onetime_reminder_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback handler for one-time event reminders
    @param update: update.callback_query != none
    @param context: unused
    @return: none
    """
    query = update.callback_query
    await query.answer()
    length, unit = query.data.split("-")
    length = int(length)
    res = await query.message.reply_text(f"Set {length} {unit[:len(unit)-1]} reminder.")
    return res


def add_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ot", onetime_start))
    application.add_handler(CallbackQueryHandler(onetime_reminder_callback_handler))


def main() -> None:
    application = Application.builder().token(os.getenv("TELEGRAM_API_KEY")).build()
    add_handlers(application)
    application.run_polling()


if __name__ == "__main__":
    main()



