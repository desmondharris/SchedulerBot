"""
Create a PersistentBot Class that will expand the functionality of the Bot class. It will NOT inherit from the Bot class.
It will be able to create events, commands, and tasks that will be persistent across multiple sessions.
"""
import logging

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import (
    ApplicationBuilder,
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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Turn off logging for HTTP POST requests
logging.getLogger("httpx").setLevel(logging.WARNING)


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

        # Add and configure handlers
        self.app.add_handler(CommandHandler("start", self.launch_web_ui))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self.web_app_data))

    def start_bot(self):
        self.app.run_polling()

    async def launch_web_ui(self, update: Update, callback: ContextTypes.DEFAULT_TYPE):

        # Add user to database
        cursor = self.conn.cursor(buffered=True)
        cursor.execute("SELECT * FROM users WHERE chatid=%s", (update.message.chat_id,))
        user_exists = cursor.fetchone()

        if not user_exists:
            query = "INSERT INTO users (chatid) VALUES (%s) ON DUPLICATE KEY UPDATE chatid=chatid;"
            values = (update.message.chat_id,)
            cursor.execute(query, values)
        self.conn.commit()
        cursor.close()

        # display our web-app!
        kb = [
            [KeyboardButton(
                "Go to bot portal",
                web_app=WebAppInfo("https://related-currently-maggot.ngrok-free.app")
            )]
        ]
        await update.message.reply_text("Let's do this...", reply_markup=ReplyKeyboardMarkup(kb))

    async def web_app_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        data = json.loads(update.message.web_app_data.data)
        await update.message.reply_text("Your data was:")
        await update.message.reply_text(f"{data}")
        split_data = data.split('~')
        match split_data[0]:
            case "NONRECURRINGEVENT":
                                                                 #name           datetime (YYYY-MM-DD HH:MM)
                self.create_nr_event(update.message.chat_id, split_data[1], datetime.datetime.strptime(' '.join([split_data[2], split_data[3]]), "%Y-%m-%d %H:%M"))

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





b = PersistentBot()
b.start_bot()
