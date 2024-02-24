"""
Create a PersistentBot Class that will expand the functionality of the Bot class. It will NOT inherit from the Bot class.
It will be able to create events, commands, and tasks that will be persistent across multiple sessions.
"""
import logging

import telegram
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    Defaults,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)


import schedule
import datetime, pytz

import requests, json
import os, sys

from Calendar import Event
from Keys import TELEGRAM_API_KEY, TELEGRAM_USER_ID, WEATHER_API_KEY

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

        # Add and configure handlers
        self.app.add_handler(CommandHandler("start", self.launch_web_ui))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self.web_app_data))

    def start_bot(self):
        self.app.run_polling()

    async def launch_web_ui(self, update: Update, callback: ContextTypes.DEFAULT_TYPE):
        # display our web-app!
        kb = [
            [KeyboardButton(
                "Show me my Web-App!",
                web_app=WebAppInfo("https://related-currently-maggot.ngrok-free.app/")
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
                self.create_nr_event(split_data[1], datetime.datetime.strptime(' '.join([split_data[2], split_data[3]]), "%Y-%m-%d %H:%M"))

        print(data.split('~'))

    def create_nr_event(self, name: str, event_time: datetime.datetime):
        # Send message at event time
        self.app.job_queue.run_once(self.event_now, event_time, data={
            'name': name,
            'time': event_time,
            'chat_id': TELEGRAM_USER_ID
        })
        # Set reminders
        # NOTE: apscheduler automatically handles events that are in the past, this could
        # cause issues in the future?
        self.event_set_reminder(name, event_time, days=0, hours=0, minutes=15)
        self.event_set_reminder(name, event_time, days=0, hours=1, minutes=0)
        self.event_set_reminder(name, event_time, days=0, hours=4, minutes=0)
        self.event_set_reminder(name, event_time, days=1, hours=0, minutes=0)
        self.event_set_reminder(name, event_time, days=5, hours=0, minutes=0)

    async def event_now(self, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(context.job.data['chat_id'], f"Event {context.job.data['name']} is happening now!")

    def event_set_reminder(self, name: str, event_time: datetime.datetime, days=0, hours=0, minutes=0):
        reminder_time = event_time - datetime.timedelta(days=days, hours=hours, minutes=minutes)
        if reminder_time < datetime.datetime.now():
            return
        self.app.job_queue.run_once(self.event_send_reminder, reminder_time, data={
            'name': name,
            'time': event_time,
            'chat_id': TELEGRAM_USER_ID
        })

    async def event_send_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(context.job.data['chat_id'], f"REMINDER: {context.job.data['name']} at {context.job.data['time']}")



b = PersistentBot()
b.start_bot()
