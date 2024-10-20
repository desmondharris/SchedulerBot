"""
TODO:
- Make build_from_old method
- Make bot persistent

1. Write More Unit Tests
3. Allow users to delete events
    - query for all users events, include event id
    - use todolist structure built from JobQueue.jobs(), set onclick actions to delete Job add event id to a list
    - delete events, reminders
5. Implement Weather.py
6. Add timezone handling for US
"""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import CallbackQuery
from telegram.ext import (
    ApplicationBuilder,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    CommandHandler,
    Defaults,
    MessageHandler,
    filters,
    CallbackContext,
)

import sys
import datetime
import pytz
import json
import logging
from typing import Callable
from peewee import DoesNotExist, OperationalError
import functools
from apscheduler.jobstores.base import JobLookupError

from src.Keys import Key
from src.BotSQL import Chat, NonRecurringEvent, RecurringEvent, ToDo, mysql_db


# logging setup
logging.basicConfig(level=logging.ERROR,
                    format="%(name)s :[ %(asctime)s ] %(levelname)s message near line %(lineno)d in %(funcName)s --> "
                           "%(filename)s \n%(message)s\n",
                    handlers=[
                        # Save logs to file and print to stdout
                        logging.FileHandler("Bot.log", mode='w'),
                        logging.StreamHandler(sys.stdout)
                    ])
logger = logging.getLogger("Bot")
logger.setLevel(logging.DEBUG)

# Remove unneeded logs from libraries
for logger_name, logger_obj in logging.root.manager.loggerDict.items():
    if logger_name != "Bot":
        # Check if the obtained object is actually a logger
        if isinstance(logger_obj, logging.Logger):
            logger_obj.setLevel(logging.ERROR)

START, WEBAPP, GETZIP = range(3)
CHECK_CHAR = '✅'
UNCHECK_CHAR = '⬜'

if __name__ == "__main__":
    logger.info("PersistentBot module started")


async def clean_todo(update: Update):
    query = ToDo.delete().where(ToDo.done==True and ToDo.user == update.message.from_user.id)
    query.execute()
    items = ToDo.select().where(ToDo.user == update.message.chat_id)
    kb = []
    [kb.append([InlineKeyboardButton(f"{CHECK_CHAR if item.done else UNCHECK_CHAR} {item.text}",
                                     callback_data=f"toggle__{item.id}")]) for item in items]
    kb.append([InlineKeyboardButton("Click here to remove finished items", callback_data="CLEAR")])
    kb = InlineKeyboardMarkup(kb)
    await update.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=query.message.text,
        reply_markup=kb
    )


def catch_all(func: Callable) -> Callable:
    # TODO: add a rebuild cl option/flag
    """
    This is a decorator used to catch all errors that occur during bot polling. It stops the program from exiting,
    creates a new bot object, and builds from the database. This function should only be called if an unexpected error
    fails to be caught by python-telegram-bot's error handling, which should never happen.
    @param func: PersistentBot.start
    @return: Wrapper function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # sys.execute("python PersistentBot.py --rebuild") something like this
        # sys.exit()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}\nArgs: {dict(zip(range(len(args)), args))}\nKwargs: {dict(zip(range(len(kwargs)), kwargs))}", exc_info=True)
    return wrapper

async def send_event_list(update: Update, context: CallbackContext):
    """Send a list of events with inline buttons to delete them."""
    user_id = update.message.chat_id
    events = NonRecurringEvent.select().where(NonRecurringEvent.user == user_id)
    if not events:
        await update.message.reply_text("You have no events.")
        return

    kb = [
        [InlineKeyboardButton(f"{event.name} at {event.date} {event.time}", callback_data=f"delete_event__{event.event_id}")]
        for event in events
    ]
    kb = InlineKeyboardMarkup(kb)
    await update.message.reply_text("Select an event to delete:", reply_markup=kb)


# Callback query handler to delete event
async def delete_event_callback(update: Update, context: CallbackContext):
    """Handle the callback query to delete an event."""
    query = update.callback_query
    event_id = query.data
    event_id = event_id.replace("delete_event__", "")
    try:
        event = NonRecurringEvent.get(NonRecurringEvent.event_id == event_id)
        job_name = f"{event.user}:REMINDER:{event.event_id}"
        try:
            context.job_queue.scheduler.remove_job(job_name)
        except JobLookupError:
            logger.error(f"Job {job_name} not found in Job Queue")

        event.delete_instance()
        await query.answer(text="Event deleted.")
        await query.edit_message_text(text=f"Deleted event: {event.name}")
    except DoesNotExist:
        await query.answer(text="Event not found.")
        await query.edit_message_text(text="Event not found.")

async def todo_toggle(update: Update, context) -> None:
    """
    This function is used to toggle the to-do list of the user when they change it using the inline keyboard.
    It also updates the database.
    @param update: telegram api
    @param context: telegram api
    """
    query = update.callback_query

    if query.data == "CLEAR":
        sql_query = ToDo.delete().where(ToDo.done == True, ToDo.user == query.message.chat_id)
        sql_query.execute()
    else:
        id = query.data.replace("toggle__", '')
        todo = ToDo.get(ToDo.id == id)
        tog = not todo.done
        ToDo.update(done=tog).where(ToDo.id == id).execute()

    items = ToDo.select().where(ToDo.user == query.message.chat_id)
    kb = []
    [kb.append([InlineKeyboardButton(f"{CHECK_CHAR if item.done else UNCHECK_CHAR} {item.text}",
                                callback_data=f"toggle__{item.id}")]) for item in items]
    kb.append([InlineKeyboardButton("Click here to remove finished items", callback_data="CLEAR")])
    kb = InlineKeyboardMarkup(kb)

    await context.bot.edit_message_text(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=query.message.text,
        reply_markup=kb
    )

async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This function sends the user a message with their to-do list.
    @param update: telegram api
    @param context: telegram api
    """
    try:
        # If user passed new item for to do list, add it to DB
        # Otherwise, display current to do list
        cmd, item = update.message.text.split()
        td = ToDo.create(user=update.message.chat_id, text=item)
        if td.id:
            logger.info(f"Created todo list item {td.id} for user {update.message.chat_id}")
        else:
            logger.error(f"Failed creating todo list item {item} for user {update.message.chat_id}")
    except ValueError:
        pass

    # Display to do list
    items = ToDo.select().where(ToDo.user == update.message.chat_id)
    kb = []
    [kb.append([InlineKeyboardButton(f"{CHECK_CHAR if item.done else UNCHECK_CHAR} {item.text}", callback_data=f"toggle__{item.id}")]) for item in items]
    kb.append([InlineKeyboardButton("Click here to remove finished items", callback_data="CLEAR")])
    kb = InlineKeyboardMarkup(kb)
    await update.message.reply_text("Your to-do list: ", reply_markup=kb)


async def zip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter your ZIP code: ")
    return GETZIP


async def get_zip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    THis function adds the user's zip code to the database and end the conversation
    @param update:
    @param context:
    @return:
    """
    zip_code = update.message.text

    # Verify ZIP code is a 5 digit integer
    try:
        if len(zip_code) != 5:
            raise ValueError
        zip_code = int(zip_code)
        # TODO: Verify zip code exists
    except ValueError:
        logger.info(f"Failed to add zip code ")
        await update.message.reply_text("Invalid ZIP code, please try again")
        return GETZIP

    # Add zip code to database
    Chat.update(zip=zip_code).where(Chat.id == update.message.chat_id).execute()
    await update.message.reply_text("Your zip code has been added!")
    return ConversationHandler.END


async def launch_web_ui(update: Update, callback: ContextTypes.DEFAULT_TYPE):
    # Display launch page
    kb = [
        [KeyboardButton(
            "Go to bot portal",
            web_app=WebAppInfo(Key.PORTAL_URL)
        )]
    ]
    await update.message.reply_text("Launching portal...", reply_markup=ReplyKeyboardMarkup(kb))


def get_nr_events_between(chat_id, start: datetime.date, end: datetime.date):
    return NonRecurringEvent.select().where(
        (NonRecurringEvent.date >= start) &
        (NonRecurringEvent.date <= end) &
        (NonRecurringEvent.user == chat_id)
    )


def user_in_db(chat_id: int):
    try:
        Chat.get_by_id(chat_id)
        return True
    except DoesNotExist:
        return False


class PersistentBot:
    def __init__(self):
        # Create bot
        self.app = ApplicationBuilder().token(Key.TELEGRAM_API_KEY).defaults(
            Defaults(tzinfo=pytz.timezone("US/Eastern"))).build()

        # Define states
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self.web_app_data))
        self.app.add_handler(CommandHandler("dailymsg", self.send_daily_message))
        self.app.add_handler(CommandHandler("new", launch_web_ui))
        self.app.add_handler(CommandHandler("removezip", self.remove_zip))
        self.app.add_handler(CommandHandler("todo", todo))
        self.app.add_handler(CommandHandler("cancel", self.cancel))
        self.app.add_handler(CommandHandler("deleteevent", send_event_list))

        # Add conversation handler to get zip code
        zip_handler = ConversationHandler(
            entry_points=[CommandHandler("zip", zip_start)],
            states={
                GETZIP: [MessageHandler(filters.TEXT, get_zip)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(zip_handler)

        # Add to do list handler
        self.app.add_handler(CallbackQueryHandler(todo_toggle, pattern="toggle__"))
        self.app.add_handler(CallbackQueryHandler(delete_event_callback, pattern="delete_event__"))

        logger.debug("Bot object created")

    async def build_from_old(self) -> None:
        """
        This method recreates a Persistent Bot object from the database after a crash or other error.
        @return: None
                reminders- list of strings like ["5-MINUTES", "1-HOURS"]
        chat_id- telegram id
        eventDate- datetime object
        eventTime- time object

        """
        # connect to database

        # add all events from tables to bot job queue
        events = NonRecurringEvent.select()
        reminders = ["5-MINUTES", "2-HOURS", "1-DAYS"]
        for e in events:
            data = {}
            data["eventId"] = e.event_id
            data["eventName"] = e.name
            data["chat_id"] = e.user.id
            data["eventDate"] = e.date
            data["eventTime"] = e.time
            self.app.job_queue.run_once(self.event_now, datetime.datetime.combine(e.date, e.time),
                                        name=f"{e.user}:REMINDER:{e.event_id}", data=data)
            for r in reminders:
                num, period = r.split("-")
                num = int(num)
                match period:
                    case "MINUTES":
                        self.event_set_reminder(data, minutes=num)
                    case "HOURS":
                        self.event_set_reminder(data, hours=num)
                    case "DAYS":
                        self.event_set_reminder(data, days=num)

    @catch_all
    def start_bot(self):
        mysql_db.connect()
        logger.info("Bot started polling")
        self.app.run_polling()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Check if user is in database
        await self.build_from_old()
        user, created = Chat.get_or_create(id=update.message.chat_id)
        if created:
            await self.app.bot.send_message(update.message.chat_id, text="Welcome to the bot! To get weather data, "
                                                                         "I need to know your ZIP code. To enter it, "
                                                                         "type /zip at anytime. This is NOT required.")
            logger.info(f"New user {update.message.chat_id}")
        else:
            await self.app.bot.send_message(update.message.chat_id, text="hello")

    """
    name: event name
    date: event date only
    time: event time only
    eventTime: time of event
    eventDate: date of event if exists
    user: chat id of context user
    """
    async def web_app_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        webapp_data = json.loads(update.message.web_app_data.data)
        webapp_data["chat_id"] = update.message.chat_id
        webapp_data["eventTime"] = datetime.datetime.strptime(webapp_data['eventTime'], "%H:%M").time()
        try:
            webapp_data["eventDate"] = datetime.datetime.strptime(webapp_data['eventDate'], "%Y-%m-%d")
        except KeyError:
            pass
        logger.debug(f"Webapp data received: {webapp_data}")

        match webapp_data["type"]:
            case "NONRECURRINGEVENT":
                await self.create_nr_event(webapp_data)
            case "RECURRINGEVENT":
                await self.create_r_event(webapp_data)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        raise ValueError

    async def event_now(self, context: ContextTypes.DEFAULT_TYPE):
        data = context.job.data
        evnt = NonRecurringEvent.get(NonRecurringEvent.event_id == data["eventId"])
        evnt.delete_instance()
        await self.app.bot.send_message(data['chat_id'], f"Event {data['eventName']} is happening now!")

    def event_set_reminder(self, evnt, minutes: int=0, hours: int=0, days: int=0):
        # Use timedelta to avoid dictionary mess
        reminder_time = datetime.datetime.combine(evnt.date, evnt.time) - datetime.timedelta(days=days, hours=hours,
                                                                                             minutes=minutes)
        if reminder_time < datetime.datetime.now():
            return
        self.app.job_queue.run_once(self.event_send_reminder, reminder_time,
                                    name=f"{evnt.user.id}:REMINDER:{evnt.event_id}", data=evnt)

    async def event_send_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        msg = f"REMINDER: {context.job.data.name} at {context.job.data.time}, {context.job.data.date}"
        await self.app.bot.send_message(context.job.data['chat_id'], msg)

    async def create_nr_event(self, data: dict):
        '''
        @param data: dictionary
        reminders- list of strings like ["5-MINUTES", "1-HOURS"]
        chat_id- telegram id
        eventDate- datetime object
        eventTime- time object

        @return: None
        '''
        # if event id exists, we are building from the database and don't need to add a new event
        if "eventId" not in data:
            # Add new event to database

            # convert list into a string for database storage
            reminders_str = ""
            for i in data["reminders"]:
                reminders_str += i


            evnt = NonRecurringEvent.create(user=data["chat_id"], name=data["eventName"], date=data["eventDate"],
                                            time=data['eventTime'], reminders=reminders_str)
            if evnt.event_id is not None:
                logger.info(f"Created event {evnt.event_id} in database")
            else:
                logger.error(f"Failed to create event with params {data}")
                return
        # Add job to job queue with formatted name
        self.app.job_queue.run_once(self.event_now, datetime.datetime.combine(evnt.date, evnt.time),
                                    name=f"{evnt.user.id}:REMINDER:{evnt.event_id}", data=data)
        if "reminders" in data:
            # TODO: Include reminders in db somehow
            for reminder in data["reminders"]:
                num, period = reminder.split("-")
                num = int(num)
                match period:
                    case "MINUTES":
                        self.event_set_reminder(evnt,  minutes=num)
                    case "HOURS":
                        self.event_set_reminder(evnt,  hours=num)
                    case "DAYS":
                        self.event_set_reminder(evnt,  days=num)
                    case "WEEKS":
                        self.event_set_reminder(evnt, days=int(7 * num))
                    # If this case executes, web app has been altered or malfunctioned
                    case _:
                        logger.error(f"CRTICAL ERROR: Received bad webapp data. {period} is not a valid time unit.")
                        raise RuntimeError("Invalid webapp data received, check logs")

        await self.app.bot.send_message(evnt.user.id, "Event has been added to your calendar!")

    async def create_r_event(self, data: dict):
        # Get a string of format DAILY, WEEKLY:MONDAY, MONTHLY:15
        try:
            freq, day = data['freq'].split('~')
        except ValueError as e:
            freq = data['freq']
            day = -1

        freq = freq.upper()

        # Add event to database
        evnt = RecurringEvent.create(user=data["chat_id"], name=data["eventName"], reccurence=freq, time=data["eventTime"])
        data['eventId'] = evnt.event_id

        # Find all the times a reminder should be sent
        remind_times = []
        for reminder in data["reminders"]:
            # In HTML, reminder have values NUMBER-UNITS
            num, time = reminder.split('-')
            num = int(num)
            match time:
                case "MINUTES":
                    change = datetime.timedelta(minutes=num)
                case "HOURS":
                    change = datetime.timedelta(hours=num)
                case _:
                    logger.error(f"CRTICAL ERROR: Received bad webapp data. {time} is not a valid time unit.")
                    return
            new_time = datetime.datetime.combine(datetime.datetime.today(), data["eventTime"]) - change
            remind_times.append(new_time.time())

        # In each block, set recurring reminders event notifs to job queue
        # In JobQueue, reminders have names like: CHATID:REMINDER/EVENT:EVENTID
        # Individual reminders for events cannot be altered.
        match freq:
            case "DAILY":
                self.app.job_queue.run_daily(self.r_event_now, data["eventTime"], days=(0, 1, 2, 3, 4, 5, 6), name=f"{data['chat_id']}:REMINDER:{data['eventId']}", data=data)
                for r_time in remind_times:
                    self.app.job_queue.run_daily(self.r_event_reminder, r_time, days=(0, 1, 2, 3, 4, 5, 6), name=f"{data['chat_id']}:REMINDER:{data['eventId']}", data=data)

            case "WEEKLY":
                days = {"Sunday": 0,
                        "Monday": 1,
                        "Tuesday": 2,
                        "Wednesday": 3,
                        "Thursday": 4,
                        "Friday": 5,
                        "Saturday": 6}

                self.app.job_queue.run_daily(self.r_event_now, data['eventTime'], days=(days[day],), name=f"{data['chat_id']}:REMINDER:{data['eventId']}",  data=data)
                for r_time in remind_times:
                    self.app.job_queue.run_daily(self.r_event_reminder, r_time, days=(days[day],), name=f"{data['chat_id']}:REMINDER:{data['eventId']}", data=data)

            case "MONTHLY":
                day = int(day)
                self.app.job_queue.run_monthly(self.r_event_now, data['eventTime'], day=day, name=f"{data['chat_id']}:REMINDER:{data['eventId']}",data=data)
                for r_time in remind_times:
                    self.app.job_queue.run_monthly(self.r_event_reminder, r_time, day=day, name=f"{data['chat_id']}:REMINDER:{data['eventId']}", data=data)

        await self.app.bot.send_message(data['chat_id'], "Event has been added to your calendar!")

    async def r_event_now(self, context: ContextTypes.DEFAULT_TYPE):
        data = context.job.data
        await self.app.bot.send_message(data['chat_id'], f"Event {data['eventName']} is happening now!")

    async def r_event_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        data = context.job.data
        await self.app.bot.send_message(data['chat_id'], f"{data['eventName']} at {data['eventTime']}")

    def daily_message(self, chatid: int):
        pass

    async def send_daily_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(update.message.chat_id, text=self.daily_message(update.message.chat_id))

    async def remove_zip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        Chat.update(zip=0).where(Chat.id == update.message.chat_id).execute()
        await self.app.bot.send_message(update.message.chat_id, text="Your ZIP code has been removed from your profile.")


if __name__ == "__main__":
    b = PersistentBot()
    b.start_bot()
