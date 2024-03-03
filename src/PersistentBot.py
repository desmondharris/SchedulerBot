"""
TODO:
- Add daily message
    -Include weather
    -Include daily events
-Add todo list
-Allow user to choose which reminders they want
-Add ability to search events table by date+user
-Add ability to delete events
-Add ability to see events for specific day, week, month
"""
import logging

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import (
    ApplicationBuilder,
    ConversationHandler,
    ContextTypes,
    CommandHandler,
    Defaults,
    MessageHandler,
    filters,
)

import mysql.connector

import datetime, pytz

import json

from Keys import TELEGRAM_API_KEY, TELEGRAM_USER_ID, WEATHER_API_KEY
from Keys import MYSQL_USER, MYSQL_PASSWORD
DEBUG = 1
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Turn off logging for HTTP POST requests
logging.getLogger("httpx").setLevel(logging.WARNING)
START, GET_ZIP, WEBAPP = range(3)

class PersistentBot:
    def __init__(self):
        # Create bot
        self.app = ApplicationBuilder().token(TELEGRAM_API_KEY).defaults(Defaults(tzinfo=pytz.timezone("US/Eastern"))).build()
        # Dummy attribute for sql connector
        self.conn = mysql.connector.connect(
            host='localhost',
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database='telegram'
        )

        # Define states
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self.web_app_data))
        self.app.add_handler(CommandHandler("dailymsg", self.send_daily_message))

    def start_bot(self):
        self.app.run_polling()

    async def get_zip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Check if user is in database
        user_chat_id = update.message.chat_id
        if not self.user_in_db(user_chat_id):
            self.db_insert("users", {"chatid": user_chat_id})
            await self.app.bot.send_message(chat_id=update.message.chat_id, text="Welcome to the bot!")
            await self.app.bot.send_message(chat_id=update.message.chat_id,text="To get weather data, I need to know your ZIP code. To enter it, type /zip at anytime")
            await self.app.bot.send_message(chat_id=update.message.chat_id, text="A ZIP code is not required")
        await self.launch_web_ui(update, context)

    async def launch_web_ui(self, update: Update, callback: ContextTypes.DEFAULT_TYPE):
        # Display launch page
        kb = [
            [KeyboardButton(
                "Go to bot portal",
                web_app=WebAppInfo("https://regularly-unbiased-stud.ngrok-free.app")
            )]
        ]
        await update.message.reply_text("Launching portal...", reply_markup=ReplyKeyboardMarkup(kb))

    async def web_app_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if DEBUG:
            print("|---DEBUGGING IN PersistentBot.web_app_data---|")
        data = json.loads(update.message.web_app_data.data)
        await update.message.reply_text("Your data was:")
        await update.message.reply_text(f"{data}")
        split_data = data.split('~')
        match split_data[0]:
            case "NONRECURRINGEVENT":
                                                                 # name           datetime (YYYY-MM-DD HH:MM)
                self.create_nr_event(update.message.chat_id, split_data[1], datetime.datetime.strptime(' '.join([split_data[2], split_data[3]]), "%Y-%m-%d %H:%M"))
            case "RECURRINGEVENT":
                if DEBUG:
                    print(split_data[1:])


    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    def create_nr_event(self, chat_id, name: str, event_time: datetime.datetime):
        # Send message at event time
        self.app.job_queue.run_once(self.event_now, event_time, data={
            'name': name,
            'datetime': event_time,
            'chat_id': chat_id
        })
        # Set reminders
        # NOTE: apscheduler automatically handles events that are in the past, this could
        # cause issues in the future?
        self.event_set_reminder(chat_id, name, event_time, days=0, hours=0, minutes=15)
        self.event_set_reminder(chat_id, name, event_time, days=0, hours=1, minutes=0)
        self.event_set_reminder(chat_id, name, event_time, days=0, hours=4, minutes=0)
        self.event_set_reminder(chat_id, name, event_time, days=1, hours=0, minutes=0)
        self.event_set_reminder(chat_id, name, event_time, days=5, hours=0, minutes=0)

        # Add event to events table
        self.db_insert("events", {"name": name, "datetime": event_time, "user": chat_id})

    async def event_now(self, context: ContextTypes.DEFAULT_TYPE):
        # Remove event from events table
        curs = self.conn.cursor(buffered=True)
        u_data = context.job.data
        # Use parameterized queries to safely pass values
        query = "DELETE FROM events WHERE user=%s AND datetime=%s AND name=%s"
        values = (u_data["chat_id"], u_data["datetime"].strftime('%Y-%m-%d %H:%M:%S'), u_data["name"])
        curs.execute(query, values)
        self.conn.commit()  # Commit changes
        curs.close()  # Close cursor

        await self.app.bot.send_message(context.job.data['chat_id'], f"Event {context.job.data['name']} is happening now!")

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

    def db_insert(self, table, data: dict):
        """
        table: str
        data: dict
        data is a dict that will contain the data to be inserted into the table
        """
        cursor = self.conn.cursor(buffered=True)
        # Insert data into table
        if table == "users":
            query = "INSERT INTO users (chatid) VALUES (%s)"

            # verify that data is an integer
            if type(data["chatid"]) is not int:
                raise ValueError(f"Table 'users' cannot have non integer chatid (got type {type(data['chatid'])})")

            values = (data['chatid'],)
            cursor.execute(query, values)
            self.conn.commit()
            cursor.close()

        elif table == "events":
            query = "INSERT INTO events(user, name, datetime) VALUES (%s, %s, %s)"
            values = (data['user'], data['name'], data['datetime'],)
            cursor.execute(query, values)
            self.conn.commit()
            cursor.close()

    def get_events_on(self, chat_id, date: datetime.date):
        cursor = self.conn.cursor(buffered=True)
        query = f'SELECT * FROM events WHERE user=%s AND datetime LIKE %s'
        values = (chat_id, f"{date.__str__().split()[0]}%")
        cursor.execute(query, values)
        return cursor.fetchall()

    def get_events_between(self, chat_id, start: datetime.date, end: datetime.date):
        cursor = self.conn.cursor(buffered=True)
        query = f'SELECT * FROM events WHERE user=%s AND datetime BETWEEN %s AND %s'
        values = (chat_id, start, end)
        cursor.execute(query, values)
        return cursor.fetchall()

    def user_in_db(self, chat_id):
        cursor = self.conn.cursor(buffered=True)
        query = "SELECT * FROM users WHERE chatid=%s"
        values = (chat_id,)
        cursor.execute(query, values)
        return cursor.fetchone() is not None

    def daily_message(self, chatid):
        if DEBUG:
            print("|---DEBUGGING IN PersistentBot.daily_message----|")
        msg = ""
        # Open database connection
        cursor = self.conn.cursor(buffered=True)
        # Get events for today
        events = self.get_events_on(chatid, datetime.date.today())

        msg += "Today's events:\n"
        for idx, event in enumerate(events):
            _, _1, event_name, event_time = event
            # get time from datetime object and convert to 12 hour time
            event_time = event_time.strftime('%I:%M %p')
            msg += f"[{idx+1}]:  {event_name} at {event_time}\n"
            if DEBUG:
                print(f"Event name: {event_name}, Event time: {event_time}")
        # Close cursor
        cursor.close()
        msg += f"{datetime.datetime.now().strftime('%A, %B %d')}\n"
        return msg

    async def send_daily_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(chat_id=update.message.chat_id, text=self.daily_message(update.message.chat_id))


b = PersistentBot()
b.start_bot()
