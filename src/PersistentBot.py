"""
TODO:
-Allow user to choose which reminders they want
- Add daily message
    -Include weather
    -Include daily events
-Add ability to see events for specific day, week, month

Shortlist:
- Send reminder info as part of jsonified string
- Handle reminder info in WebApp update function

"""
import atexit
import logging

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

import datetime
import pytz

import json

from Keys import TELEGRAM_API_KEY
from Keys import PORTAL_URL
from BotSQL import BotSQL

from pydevd_pycharm import settrace
settrace('localhost', port=9412, stdoutToServer=True, stderrToServer=True)
DEBUG = 1


@atexit.register
def cleanup():
    pass


# logging setup
logging.basicConfig(filename="Bot.log", filemode='w', level=logging.ERROR,
                    format="%(name)s :[ %(asctime)s ] %(levelname)s message near line %(lineno)d in %(funcName)s --> %(filename)s \n%(message)s\n")
logger = logging.getLogger("Bot")
logger.setLevel(logging.DEBUG)

# Remove unneeded logs from libraries
for logger_name, logger_obj in logging.root.manager.loggerDict.items():
    if logger_name != "Bot":
        # Check if the obtained object is actually a logger
        if isinstance(logger_obj, logging.Logger):
            logger_obj.setLevel(logging.ERROR)

START, GET_ZIP, WEBAPP, GETZIP = range(4)

if __name__ == "__main__":
    logger.info("PersistentBot module started")


class PersistentBot:
    def __init__(self):
        # Create bot
        self.app = ApplicationBuilder().token(TELEGRAM_API_KEY).defaults(Defaults(tzinfo=pytz.timezone("US/Eastern"))).build()

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
            await self.app.bot.send_message(
                text=f"ZIP code {zip_code} has been added to your profile! Weather data will now be added to your daily message",
                chat_id=update.message.chat_id)
            logger.info(f"ZIP code added for user {update.message.chat_id}")
        except ValueError:
            logger.error(f"Python Value Error: ZIP code {zip_code} could not be inserted for user {update.message.chat_id}")
            await self.app.bot.send_message(update.message.chat_id, text="Your ZIP is not an integer and could not be added. Please type /zip to try again")

        return ConversationHandler.END

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Check if user is in database
        user_chat_id = update.message.chat_id
        if not self.bot_sql.check_for_user(user_chat_id):
            self.bot_sql.insert("users", data={"chatid": user_chat_id})
            await self.app.bot.send_message(chat_id=update.message.chat_id, text="Welcome to the bot!")
            await self.app.bot.send_message(chat_id=update.message.chat_id, text="To get weather data, I need to know your ZIP code. To enter it, type /zip at anytime")
            await self.app.bot.send_message(chat_id=update.message.chat_id, text="A ZIP code is not required.")
            logger.info(f"New user {update.message.chat_id}")

    async def launch_web_ui(self, update: Update, callback: ContextTypes.DEFAULT_TYPE):
        # Display launch page
        kb = [
            [KeyboardButton(
                "Go to bot portal",
                web_app=WebAppInfo(PORTAL_URL)
            )]
        ]
        await update.message.reply_text("Launching portal...", reply_markup=ReplyKeyboardMarkup(kb))

    async def web_app_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if DEBUG:
            print("|---DEBUGGING IN PersistentBot.web_app_data---|")
        webapp_data = json.loads(update.message.web_app_data.data)
        await update.message.reply_text("Your data was:")
        await update.message.reply_text(f"{webapp_data}")
        if DEBUG:
            print(webapp_data)

        match webapp_data["type"]:
            case "NONRECURRINGEVENT":
                data = {
                    'name': webapp_data["name"],
                    'datetime': datetime.datetime.strptime(webapp_data["datetime"], "%Y-%m-%d %H:%M"),
                    'chat_id': update.message.chat_id,
                }
                if self.create_nr_event(data):
                    logger.info(f"Sucessfully created event for user {update.message.chat_id}")
                    await self.app.bot.send_message(update.message.chat_id, text="Event added!")
                else:
                    logger.error(f"Failed to add event for user {update.message.chat_id}")

            case "RECURRINGEVENT":
                data = {
                    "name": webapp_data["name"],
                    "recurrence": webapp_data["frequency"],
                    "time": webapp_data["time"],
                    "user": update.message.chat_id,
                }
                if self.bot_sql.insert("recurringevents", data=data):
                    logger.info(f"Recurring event added for user {update.message.chat_id}")
                    await self.app.bot.send_message(update.message.chat_id, text="Event added!")
                else:
                    logger.error(f"Error inserting recurring event {[key for key in data.keys()]}")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    def create_nr_event(self, data: dict):
        # Send message at event time
        self.app.job_queue.run_once(self.event_now, data["event_time"], data=data)
        # Set reminders
        # NOTE: apscheduler automatically handles events that are in the past, this could
        # cause issues in the future?
        self.event_set_reminder(data["chat_id"], data["name"], data["event_time"], days=0, hours=0, minutes=15)
        self.event_set_reminder(data["chat_id"], data["name"], data["event_time"], days=0, hours=1, minutes=0)
        self.event_set_reminder(data["chat_id"], data["name"], data["event_time"], days=0, hours=4, minutes=0)
        self.event_set_reminder(data["chat_id"], data["name"], data["event_time"], days=1, hours=0, minutes=0)
        self.event_set_reminder(data["chat_id"], data["name"], data["event_time"], days=5, hours=0, minutes=0)

        # Add event to events table
        data = {
            "user": data["chat_id"],
            "name": data["name"],
            "datetime": data["event_time"]
        }
        return self.bot_sql.insert("events", data=data)

    async def event_now(self, context: ContextTypes.DEFAULT_TYPE):
        data = context.job.data
        await self.app.bot.send_message(data['chat_id'], f"Event {data['name']} is happening now!")
        self.bot_sql.remove_nr_event(data["chat_id"], data["name"], data["datetime"])

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
        await self.app.bot.send_message(context.job.data['chat_id'], f"REMINDER: {context.job.data['name']} at {context.job.data['time']}")

    def create_r_event(self, chat_id, name: str, time: datetime.datetime, freq: str, day:str = None):
        # one liners :)
        freq = (f"{freq}:{day}" if day else freq).capitalize()

        self.bot_sql.insert("recurringevents", data={
            "user": chat_id,
            "name": name,
            "recurrence": freq,
            "time": time
        })

    def get_events_between(self, chat_id, start: datetime.date, end: datetime.date):
        return self.bot_sql.events_between(chat_id, start, end)

    def user_in_db(self, chat_id):
        return self.bot_sql.check_for_user(chat_id) is not None

    def daily_message(self, chatid: int):
        if DEBUG:
            print("|---DEBUGGING IN PersistentBot.daily_message----|")
        msg = ""
        # Get events for today
        events = self.bot_sql.events_on(chatid, datetime.date.today())

        msg += "Today's events:\n"
        for idx, event in enumerate(events):
            # unpack list returned by mysql
            _, _1, event_name, event_time = event
            # get time from datetime object and convert to 12 hour time
            event_time = event_time.strftime('%I:%M %p')
            msg += f"[{idx+1}]:  {event_name} at {event_time}\n"
            if DEBUG:
                print(f"Event name: {event_name}, Event time: {event_time}")

        msg += f"{datetime.datetime.now().strftime('%A, %B %d')}\n"
        return msg

    async def send_daily_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(chat_id=update.message.chat_id, text=self.daily_message(update.message.chat_id))

    async def remove_zip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.bot_sql.remove_zip(update.message.chat_id):
            await self.app.bot.send_message(chat_id=update.message.chat_id, text="Your ZIP code has been removed from your profile.")
        else:
            await self.app.bot.send_message(chat_id=update.message.chat_id,
                                            text="The system encountered an error deleting your ZIP code. Please try again later.")

    async def todo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        items = self.bot_sql.todo_items(update.message.chat_id)
        todolist = ""
        if DEBUG:
            print(items)
        for item in items:
            _, _, item = item
            todolist += item + '\n'

        return todolist


b = PersistentBot()
b.start_bot()
