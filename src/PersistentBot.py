"""
TODO:
1. Write More Unit Tests
2. Create responsive to do list
    -https://github.com/devforth/tobedo/tree/master?tab=readme-ov-file
3. Allow users to delete events
    - query for all users events, include event id
    - use todolist structure built from JobQueue.jobs(), set onclick actions to delete Job add event id to a list
    - delete events, reminders
5. Implement Weather.py
6. Add timezone handling for US
"""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    Defaults,
    MessageHandler,
    filters,
)

import sys
import datetime
import pytz
import json
import atexit
import logging
from subprocess import run
from peewee import DoesNotExist

from src.Keys import Key
from src.BotSQL import User, NonRecurringEvent, RecurringEvent

from pydevd_pycharm import settrace

# Connect to pychharm debug server
if __name__ == "__main__":
    try:
        DEBUG = int(sys.argv[1])
    except IndexError:
        DEBUG = 0
    if DEBUG:
        settrace('localhost', port=51858, stdoutToServer=True, stderrToServer=True)

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

if __name__ == "__main__":
    logger.info("PersistentBot module started")


class PersistentBot:
    def __init__(self):
        # Create bot
        self.app = ApplicationBuilder().token(Key.TELEGRAM_API_KEY).defaults(
            Defaults(tzinfo=pytz.timezone("US/Eastern"))).build()

        # Define states
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self.web_app_data))
        self.app.add_handler(CommandHandler("dailymsg", self.send_daily_message))
        self.app.add_handler(CommandHandler("new", self.launch_web_ui))
        self.app.add_handler(CommandHandler("removezip", self.remove_zip))
        self.app.add_handler(CommandHandler("todo", self.todo))

        # Add conversation handler to get zip code
        zip_handler = ConversationHandler(
            entry_points=[CommandHandler("zip", self.zip)],
            states={
                GETZIP: [MessageHandler(filters.TEXT, self.get_zip)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(zip_handler)

    def start_bot(self):
        logger.info("Bot started polling")
        self.app.run_polling()

    async def zip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Enter your ZIP code: ")
        return GETZIP

    async def get_zip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        zip_code = update.message.text

        # Verify ZIP code is a 5 digit integer
        try:
            if len(zip_code) != 5:
                raise ValueError
            zip_code = int(zip_code)
            # TODO: Verify zip code exists
        except ValueError:
            await update.message.reply_text("Invalid ZIP code, please try again")
            return GETZIP

        # Add zip code to database
        User.update(zip=zip_code).where(User.id == update.message.chat_id).execute()
        await update.message.reply_text("Your zip code has been added!")
        return ConversationHandler.END

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Check if user is in database
        user, created = User.get_or_create(id=update.message.chat_id)
        if created:
            await self.app.bot.send_message(update.message.chat_id, text="Welcome to the bot! To get weather data, "
                                                                         "I need to know your ZIP code. To enter it, "
                                                                         "type /zip at anytime. This is NOT required.")
            logger.info(f"New user {update.message.chat_id}")
        else:
            await self.app.bot.send_message(update.message.chat_id, text="hello")

    async def launch_web_ui(self, update: Update, callback: ContextTypes.DEFAULT_TYPE):
        # Display launch page
        kb = [
            [KeyboardButton(
                "Go to bot portal",
                web_app=WebAppInfo(Key.PORTAL_URL)
            )]
        ]
        await update.message.reply_text("Launching portal...", reply_markup=ReplyKeyboardMarkup(kb))

    """
    TODO: Change all these dicts to use common variable names.
    name: event name
    date: event date only
    time: event time only
    datetime: datetime of event
    user: chat id of context user
    """
    async def web_app_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        webapp_data = json.loads(update.message.web_app_data.data)
        webapp_data["chat_id"] = update.message.chat_id
        webapp_data["eventTime"] = datetime.datetime.strptime(webapp_data['eventTime'], "%H:%M").time()
        logger.debug(f"Webapp data received: {webapp_data}")

        match webapp_data["type"]:
            case "NONRECURRINGEVENT":
                self.create_nr_event(webapp_data)
            case "RECURRINGEVENT":
                self.create_r_event(webapp_data)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    async def event_now(self, context: ContextTypes.DEFAULT_TYPE):
        data = context.job.data
        evnt = NonRecurringEvent.get(NonRecurringEvent.event_id == data["eventId"])
        evnt.delete_instance()
        await self.app.bot.send_message(data['chat_id'], f"Event {data['eventName']} is happening now!")
        NonRecurringEvent.delete().where(NonRecurringEvent)

    def event_set_reminder(self, chat_id, name: str, event_time: datetime.datetime, days=0, hours=0, minutes=0):
        # Use timedelta to avoid dictionary mess
        reminder_time = event_time - datetime.timedelta(days=days, hours=hours, minutes=minutes)
        if reminder_time < datetime.datetime.now():
            return
        self.app.job_queue.run_once(self.event_send_reminder, reminder_time, data={
            'eventName': name,
            'eventTime': event_time,
            'chat_id': chat_id
        })

    async def event_send_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(context.job.data['chat_id'],
                                        f"REMINDER: {context.job.data['name']} at {context.job.data['time']}")

    def create_nr_event(self, data: dict):
        # data["eventTime"] = datetime.datetime.strptime(f"{data['eventDate']} {data['eventTime']}", "%Y-%m-%d %H:%M")
        evnt = NonRecurringEvent.create(user=data["chat_id"], name=data["eventName"], date=data["eventDate"],
                                        time=data['eventTime'])
        data["eventId"] = evnt.id
        data["eventDate"] = datetime.datetime.strptime(data['eventDate'], "%Y-%m-%d")
        self.app.job_queue.run_once(self.event_now, datetime.datetime.combine(data["eventDate"], data["eventTime"]), data=data)
        event_dt = datetime.datetime.combine(data['eventDate'], data['eventTime'])
        for reminder in data["reminders"]:
            num, period = reminder.split("-")
            num = int(num)
            match period:
                case "MINUTES":
                    self.event_set_reminder(data["chat_id"], data["eventName"], event_dt, minutes=num)
                case "HOURS":
                    self.event_set_reminder(data["chat_id"], data["eventName"], event_dt, hours=num)
                case "DAYS":
                    self.event_set_reminder(data["chat_id"], data["eventName"], event_dt, days=num)
                case "WEEKS":
                    self.event_set_reminder(data["chat_id"], data["eventName"], event_dt,
                                            days=int(7 * num))

    def create_r_event(self, data: dict):
        # Get a string of format DAILY, WEEKLY:MONDAY, MONTHLY:15
        freq, day = data['freq'].split('~')
        freq = freq.upper()

        # Add event to database
        evnt = RecurringEvent.create(user=data["chat_id"], name=data["eventName"], reccurence=freq, time=data["eventTime"])
        data['eventId'] = evnt.event_id

        # Find all the times a reminder should be sent
        remind_times = []
        for reminder in data["reminders"]:
            num, time = reminder.split('-')
            num = int(num)
            match time:
                case "MINUTES":
                    change = datetime.timedelta(minutes=num)
                case "HOURS":
                    change = datetime.timedelta(hours=num)
            new_time = datetime.datetime.combine(datetime.datetime.today(), data["eventTime"]) - change
            remind_times.append(new_time.time())

        # In each block, set recurring reminders event notifs to job queue
        match freq:
            case "DAILY":
                self.app.job_queue.run_daily(self.r_event_now, data["eventTime"], days=(0, 1, 2, 3, 4, 5, 6), data=data)
                for r_time in remind_times:
                    self.app.job_queue.run_daily(self.r_event_reminder, r_time, days=(0, 1, 2, 3, 4, 5, 6), data=data)

            case "WEEKLY":
                days = {"Sunday": 0,
                        "Monday": 1,
                        "Tuesday": 2,
                        "Wednesday": 3,
                        "Thursday": 4,
                        "Friday": 5,
                        "Saturday": 6}

                self.app.job_queue.run_daily(self.r_event_now, data['eventTime'], days=(days[day],), data=data)
                for r_time in remind_times:
                    self.app.job_queue.run_daily(self.r_event_reminder, r_time, days=(days[day],), data=data)

            case "MONTHLY":
                day = int(day)
                self.app.job_queue.run_monthly(self.r_event_now, data['eventTime'], day=day, data=data)
                for r_time in remind_times:
                    self.app.job_queue.run_monthly(self.r_event_reminder, r_time, day=day, data=data)

    async def r_event_now(self, context: ContextTypes.DEFAULT_TYPE):
        data = context.job.data
        await self.app.bot.send_message(data['chat_id'], f"Event {data['eventName']} is happening now!")

    async def r_event_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        data = context.job.data
        await self.app.bot.send_message(data['chat_id'], f"{data['eventName']} at {data['eventTime']}")
    def r_event_set_reminder(self, data: dict, minutes: int = 0, hours: int=0, days: int = 0):
        pass

    def get_nr_events_between(self, chat_id, start: datetime.date, end: datetime.date):
        return NonRecurringEvent.select().where(
            (NonRecurringEvent.date >= start) &
            (NonRecurringEvent.date <= end) &
            (NonRecurringEvent.user == chat_id)
        )

    def user_in_db(self, chat_id: int):
        try:
            User.get_by_id(chat_id)
            return True
        except DoesNotExist:
            return False

    def daily_message(self, chatid: int):
        pass

    async def send_daily_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(update.message.chat_id, text=self.daily_message(update.message.chat_id))

    async def remove_zip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        User.update(zip=0).where(User.id == update.message.chat_id).execute()
        await self.app.bot.send_message(update.message.chat_id, text="Your ZIP code has been removed from your profile.")

    async def todo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass


if __name__ == "__main__":
    b = PersistentBot()
    b.start_bot()
