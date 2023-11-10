"""
Create a PersistentBot Class that will expand the functionality of the Bot class. It will NOT inherit from the Bot class.
It will be able to create events, commands, and tasks that will be persistent across multiple sessions.
"""
import logging

import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    Defaults,
    ConversationHandler,
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


class PersistentBot:
    def __init__(self):
        # Dummy attributes
        self.user_ids = []

        self.app = ApplicationBuilder().token(TELEGRAM_API_KEY).defaults(Defaults(tzinfo=pytz.timezone("US/Eastern"))).build()

        # Create user directory in cwd
        self.user_dir = os.path.join(os.getcwd(), "users")
        os.mkdir(self.user_dir) if not os.path.exists(self.user_dir) else None

        # Add and configure handlers
        add_handler = ConversationHandler(
            entry_points=[CommandHandler("add", self.add)],
            states={
                'event': [MessageHandler(filters.TEXT, self.get_event_info)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        self.app.add_handler(add_handler)
    def start_bot(self):
        """
        Start the bot
        """
        self.app.run_polling()

    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Add an event or assignment to users schedule, or to-do item to to-do list
        """
        # Create buttons 
        keyboard = [
            [
                telegram.InlineKeyboardButton(text="Event", callback_data="event_get_date"),
                telegram.InlineKeyboardButton(text="Recurring Event", callback_data="get_date"),
            ],
            [telegram.InlineKeyboardButton(text="To-do"), telegram.InlineKeyboardButton(text="Assignment")],
            [telegram.InlineKeyboardButton(text="Food"),telegram.InlineKeyboardButton(text="Cancel")],
        ]
        keyboard = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("What would you like to add?", reply_markup=keyboard)
        return ConversationHandler.END
    
    
    async def event_get_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Get the date of the event
        """
        await update.message.reply_text("When is the event? (Omit year if this year) (MM/DD/YYYY)")
        return "event_get_time"

    async def event_get_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Get the time of the event
        """
        # Convert date to datetime object
        date = update.message.text
        date = datetime.datetime.strptime(date, "%m/%d/%Y")

        context.job.data["date"] = update.message.text
        await update.message.reply_text("When is the event? (HH:MM)")
        return "event_get_name"

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Cancel the current conversation
        """
        pass

    def build_from_old(self):
        """
        Build the bot from previous sessions
        """
        # Add all previous users to user_ids
        self.user_ids = []
        for user in os.listdir(self.user_dir):
            self.user_ids.append(user)
            # TODO: read all events, assignments, todos, etc from user/user_id and add them to the bot


b = PersistentBot()
b.start_bot()