import datetime
import logging
import os
import asyncio

from dotenv import load_dotenv

import peewee

import telegram
from telegram import ForceReply, Update, Message, MessageEntity, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

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


async def onetime_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        return res
    else:
        logger.warning(f"User {update.effective_user} in chat {update.effective_chat} attempted invalid ote")
        await update.message.reply_text("Please input a one-time event in one of the proper formats!")



"""
Replace web app with:
monday 1700 Brown Fellow meeting
bot replies with checklist of options
"""


def main() -> None:
    application = Application.builder().token(os.getenv("TELEGRAM_API_KEY")).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ot", onetime_start))
    application.run_polling()


if __name__ == "__main__":
    main()



