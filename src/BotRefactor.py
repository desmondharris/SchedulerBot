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

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

def weekday_to_datetime(weekday: str, time: str = "1200") -> datetime.datetime:
    """
    Given a weekday string, find the next occurence of that day and return it as a datetime object
    @param weekday:
    @param time:
    @return:
    """
    if weekday not in WEEKDAYS:
        raise ValueError("Invalid weekday")
    weekday_int = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }
    target = weekday_int[weekday]
    today = datetime.date.today()
    today = (today.weekday(), today.month, today.day)
    diff = target - today[0]
    new_time = datetime.datetime.today()
    if diff < 0:
        # TODO: Check this more thoroughly
        new_time = new_time + datetime.timedelta(days=7 - diff)
    else:
        new_time = new_time + datetime.timedelta(days=diff)
    new_time = new_time.replace(hour=int(time[:2]), minute=int(time[2:]))
    return new_time




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

    if info.split()[1].lower() in months:
        pass
    elif info.split()[1].lower() in WEEKDAYS:
        _, weekday, time, event_name = info.split(maxsplit=3)
        if len(time) != 4:
            logger.warning(f"User {update.effective_user} in chat {update.effective_chat} attempted invalid ote")
            return await update.message.reply_text("Please input a one-time event in one of the proper formats!")

        logger.debug((weekday, time, event_name))
        res = await update.message.reply_text(WEEKDAY_INLINE_TEXT, reply_markup=WEEKDAY_INLINE_KB)
        t = weekday_to_datetime(weekday, time)
        t = t.replace(second=0, microsecond=0)
        NonRecurringEvent.create(
            user=update.effective_chat.id,
            name=event_name,
            date=datetime.date.today(),
            time=t,
            reminders="",
            reminder_open = True
        )
        return res
    else:
        logger.warning(f"User {update.effective_user} in chat {update.effective_chat} attempted invalid ote")
        return await update.message.reply_text("Please input a one-time event in one of the proper formats!")


async def onetime_reminder_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback handler for one-time event reminders
    @param update: update.callback_query != none
    @param context: unused
    @return: none
    """
    query = update.callback_query
    await query.answer()

    # Find event with open reminder flag
    events = NonRecurringEvent.select().where(NonRecurringEvent.reminder_open == True)
    match len(events):
        case 0:
            logger.error("Could not find event with open reminder flag")
            return
        case 1:
            event = events[0]
        case _:
            logger.error("Multiple events with open reminder flag")
            return

    # TODO: do this automatically after 25 seconds if user doesn't press done.
    if query.data == "close-reminder":
        event.reminder_open = False
        event.save()
        return await query.message.reply_text("Reminders set.")

    # callback data is in format 5-minutes, 15-minutes, etc
    length, unit = query.data.split("-")
    length = int(length)
    res = await query.message.reply_text(f"Set {length} {unit[:len(unit) - 1]} reminder.")
    # add current reminder to event
    event = events[0]
    reminders = event.reminders
    reminders += query.data
    reminders += ","
    event.reminders = reminders
    event.save()
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
