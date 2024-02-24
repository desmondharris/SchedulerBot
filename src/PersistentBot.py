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
        # Dummy attributes
        self.user_ids = []
        self.basic_event_queue = []
        self.recurring_event_queue = []

        self.app = ApplicationBuilder().token(TELEGRAM_API_KEY).defaults(Defaults(tzinfo=pytz.timezone("US/Eastern"))).build()

        # Create user directory in cwd
        self.user_dir = os.path.join(os.getcwd(), "users")
        os.mkdir(self.user_dir) if not os.path.exists(self.user_dir) else None

        # Add and configure handlers
        self.app.add_handler(CommandHandler("start", self.launch_web_ui))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self.web_app_data))
        #self.build_from_old()

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
                self.create_nr_event(split_data[1], split_data[2], split_data[3])
        print(data.split('~'))

    def create_nr_event(self, name, date, time):
        pass


b = PersistentBot()
b.start_bot()
