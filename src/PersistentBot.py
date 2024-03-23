"""
TODO:
1. Write Unit Tests
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
                    format="%(name)s :[ %(asctime)s ] %(levelname)s message near line %(lineno)d in %(funcName)s --> %(filename)s \n%(message)s\n",
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

        # Connect database
        self.bot_sql = BotSQL()

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
        # Verify that the zip code is valid
        if len(zip_code) != 5:
            await update.message.reply_text("Invalid ZIP code, please try again")
            return GETZIP
        try:
            zip_code = int(zip_code)
            # Add zip code to database
            self.bot_sql.insert_zip(update.message.chat_id, zip_code)
            await self.app.bot.send_message(update.message.chat_id,
                                            text=f"ZIP code {zip_code} has been added to your profile! Weather data will now be added to your daily message",
                                            )
            logger.info(f"ZIP code added for user {update.message.chat_id}")
        except ValueError:
            logger.error(f"Value Error: ZIP code {zip_code} could not be inserted for user {update.message.chat_id}")
            await self.app.bot.send_message(update.message.chat_id,
                                            text="Your ZIP is not an integer and could not be added. Please type /zip to try again")

        return ConversationHandler.END

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Check if user is in database
        user, created = User.get_or_create(id=update.message.chat_id)
        if created:
            await self.app.bot.send_message(update.message.chat_id, text="Welcome to the bot! To get weather data, I need to know your ZIP code. To enter it, type /zip at anytime. This is NOT required.")
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
        print(update.message.web_app_data.data)
        webapp_data = json.loads(update.message.web_app_data.data)
        webapp_data["chat_id"] = update.message.chat_id
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
        await self.app.bot.send_message(data['chat_id'], f"Event {data['name']} is happening now!")
        self.bot_sql.remove_nr_event(data["chat_id"], data["eventName"], data["datetime"])

    def event_set_reminder(self, chat_id, name: str, event_time: datetime.datetime, days=0, hours=0, minutes=0):
        # Use timedelta to avoid dictionary mess
        reminder_time = event_time - datetime.timedelta(days=days, hours=hours, minutes=minutes)
        if reminder_time < datetime.datetime.now():
            return
        self.app.job_queue.run_once(self.event_send_reminder, reminder_time, data={
            'name': name,
            'time': event_time,
            'chat_id': chat_id
        })

    async def event_send_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(context.job.data['chat_id'],
                                        f"REMINDER: {context.job.data['name']} at {context.job.data['time']}")

    def create_nr_event(self, data: dict):
        data["eventTime"] = datetime.datetime.strptime(f"{data['eventDate']} {data['eventTime']}", "%Y-%m-%d %H:%M")
        NonRecurringEvent.create(user=data["chat_id"], name=data["eventName"], datetime=data["eventTime"])
        self.app.job_queue.run_once(self.event_now, data["eventTime"], data=data)
        for reminder in data["reminders"]:
            num, period = reminder.split("-")
            num = int(num)
            match period:
                case "MINUTES":
                    self.event_set_reminder(data["chat_id"], data["eventName"], data["eventTime"], minutes=num)
                case "HOURS":
                    self.event_set_reminder(data["chat_id"], data["eventName"], data["eventTime"], hours=num)
                case "DAYS":
                    self.event_set_reminder(data["chat_id"], data["eventName"], data["eventTime"], days=num)
                case "WEEKS":
                    self.event_set_reminder(data["chat_id"], data["eventName"], data["eventTime"],
                                            days=int(7 * num))

    def create_r_event(self, data: dict):
        freq = (f"{data['freq']}:{data['day']}" if data["day"] else data["freq"]).capitalize()
        time = datetime.datetime.strptime(data["eventTime"], "%H:%M")
        RecurringEvent.create(user=data["chat_id"], name=data["eventName"], reccurence=freq, time=time)

        # In each block, set recurring reminders event notifs to job queue
        match freq:
            case "DAILY":
                pass
            case "WEEKLY":
                pass
            case "MONTHLY":
                pass


    def r_event_set_reminder(self, data: dict, minutes: int = 0, hours: int=0, days: int = 0):
        pass
    def get_events_between(self, chat_id, start: datetime.date, end: datetime.date):
        return self.bot_sql.events_between(chat_id, start, end)

    def user_in_db(self, chat_id):
        return self.bot_sql.check_for_user(chat_id) is not None

    def daily_message(self, chatid: int):
        msg = ""
        # Get events for today
        events = self.bot_sql.events_on(chatid, datetime.date.today())

        msg += "Today's events:\n"
        for idx, event in enumerate(events):
            # unpack list returned by mysql
            _, _1, event_name, event_time = event
            # get time from datetime object and convert to 12 hour time
            event_time = event_time.strftime('%I:%M %p')
            msg += f"[{idx + 1}]:  {event_name} at {event_time}\n"

        msg += f"{datetime.datetime.now().strftime('%A, %B %d')}\n"
        return msg

    async def send_daily_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(update.message.chat_id, text=self.daily_message(update.message.chat_id))

    async def remove_zip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.bot_sql.remove_zip(update.message.chat_id):
            await self.app.bot.send_message(update.message.chat_id,
                                            text="Your ZIP code has been removed from your profile.")
        else:
            await self.app.bot.send_message(update.message.chat_id,
                                            text="The system encountered an error deleting your ZIP code. Please try again later.")

    async def todo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        items = self.bot_sql.todo_items(update.message.chat_id)
        todolist = ""
        for item in items:
            _, _, item = item
            todolist += item + '\n'

        return todolist


if __name__ == "__main__":
    b = PersistentBot()
    b.start_bot()
