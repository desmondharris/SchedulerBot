"""
Create a PersistentBot Class that will expand the functionality of the Bot class. It will NOT inherit from the Bot class.
It will be able to create events, commands, and tasks that will be persistent across multiple sessions.
"""
import logging

import telegram
from telegram import Update, ReplyKeyboardMarkup
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


class PersistentBot:
    def __init__(self):
        # Dummy attributes
        self.user_ids = []
        self.basic_event_queue = []

        self.app = ApplicationBuilder().token(TELEGRAM_API_KEY).defaults(Defaults(tzinfo=pytz.timezone("US/Eastern"))).build()

        # Create user directory in cwd
        self.user_dir = os.path.join(os.getcwd(), "users")
        os.mkdir(self.user_dir) if not os.path.exists(self.user_dir) else None

        # Add and configure handlers
        add_handler = ConversationHandler(
            entry_points=[CommandHandler("add", self.add)],
            states={
                'event': [MessageHandler(filters.TEXT, self.event_get_date)],
                'switch': [
                    MessageHandler(
                        filters.Regex("^Event$"), self.event_get_date
                    ),
                ],
                'event_get_date': [MessageHandler(filters.TEXT, self.event_get_date)],
                'event_get_time': [MessageHandler(filters.TEXT, self.event_get_time)],
                'event_get_name': [MessageHandler(filters.TEXT, self.event_get_name)],
                'event_finish': [MessageHandler(filters.TEXT, self.event_finish)],

            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        self.app.add_handler(add_handler)
        self.build_from_old()


    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Add an event or assignment to users schedule, or to-do item to to-do list
        """
        # Create buttons
        keyboard = [
            ["Event", "Recurring Event"],
            ["To-do", "Assignment"],
            ["Food", "Cancel"]
        ]

        keyboard = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

        await update.message.reply_text("What would you like to add?", reply_markup=keyboard)
        return "switch"

    async def event_get_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Get the date of the event
        """
        print("ok")
        await update.message.reply_text("When is the event? (Omit year if this year) (MM/DD/YYYY)")
        return "event_get_time"

    async def event_get_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Get the time of the event
        """
        # Convert date to datetime object
        date = update.message.text
        if len(date.split('/')) == 2:
            date = datetime.datetime.strptime(date, "%m/%d").date()
            date = date.replace(year=datetime.datetime.now().year)
        else:
            date = datetime.datetime.strptime(date, "%m/%d/%Y").date()

        context.user_data["date"] = date
        await update.message.reply_text("When is the event? (HH:MM)")
        return "event_get_name"

    async def event_get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Get the name of the event
        """
        time = update.message.text

        # Create time object
        time = datetime.datetime.strptime(time, "%H:%M").time()
        # Combine date and time
        time = datetime.datetime.combine(context.user_data["date"], time)
        context.user_data["time"] = time

        await update.message.reply_text("What is the name of the event?")
        return "event_finish"

    async def send_event(self, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(chat_id=context.job.data["user_id"], text=f"Event: {context.job.data['name']} at {context.job.data['time']}")

    async def send_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(chat_id=context.job.data["user_id"], text=f"Reminder: {context.job.data['name']} in {context.job.data['in']} at {context.job.data['time']}")

    async def event_finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Finish adding the event
        """
        name = update.message.text
        context.user_data["name"] = name

        # Calculate time difference between now and event time
        time_diff = context.user_data["time"] - datetime.datetime.now()
        time_diff = time_diff.total_seconds()

        context.user_data["user_id"] = update.message.chat_id

        # Check if event is in the past
        if time_diff < 0:
            await update.message.reply_text("Event is in the past. Please try again.")
            return ConversationHandler.END

        self.app.job_queue.run_once(self.send_event, time_diff, data=context.user_data)

        # Check if event is 30 minutes or more in the future, and add reminder if it is
        if time_diff > 1800:
            self.app.job_queue.run_once(self.send_reminder, time_diff - 1800, data={
                'name': context.user_data["name"],
                'time': context.user_data["time"],
                'user_id': context.user_data["user_id"],
                'in': "30 minutes"
            })

        # Check if event is 2 hours or more in the future, and add reminder if it is
        if time_diff > 7200:
            self.app.job_queue.run_once(self.send_reminder, time_diff - 7200, data={
                'name': context.user_data["name"],
                'time': context.user_data["time"],
                'user_id': context.user_data["user_id"],
                'in': "2 hours"
            })

        # Check if event is 1 day or more in the future, and add reminder if it is
        if time_diff > 86400:
            self.app.job_queue.run_once(self.send_reminder, time_diff - 86400, data={
                'name': context.user_data["name"],
                'time': context.user_data["time"],
                'user_id': context.user_data["user_id"],
                'in': "1 day"
            })

        # Check if event is 1 week or more in the future, and add reminder if it is
        if time_diff > 604800:
            self.app.job_queue.run_once(self.send_reminder, time_diff - 604800, data={
                'name': context.user_data["name"],
                'time': context.user_data["time"],
                'user_id': context.user_data["user_id"],
                'in': "1 week"
            })

        # Add event to user's events
        user_dir = os.path.join(self.user_dir, str(update.message.chat_id))
        os.mkdir(user_dir) if not os.path.exists(user_dir) else None

        with open(os.path.join(user_dir, "events.txt"), "a") as f:
            f.write(f"{context.user_data['name']},{context.user_data['time']}\n")

        self.basic_event_queue.append({'name': context.user_data["name"], 'time': context.user_data["time"]})
        return ConversationHandler.END

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
            # TODO: read all assignments, todos, etc from user/user_id and add them to the bot

            # Read all events from user/user_id and add them to the bot
            with open(os.path.join(self.user_dir, user, "events.txt"), "r") as f:
                for line in f.readlines():
                    line = line.split(',')
                    time = datetime.datetime.strptime(line[1][:len(line[1]) - 1], "%Y-%m-%d %H:%M:%S")
                    self.basic_event_queue.append({'name': line[0], 'time': time})

                    # Calculate time difference between now and event time
                    time_diff = time - datetime.datetime.now()
                    time_diff = time_diff.total_seconds()

                    # Check if event is in the past
                    if time_diff < 0:
                        continue

                    self.app.job_queue.run_once(self.send_event, time_diff, data={
                        'name': line[0],
                        'time': line[1],
                        'user_id': user
                    })

                    # Check if event is 30 minutes or more in the future, and add reminder if it is
                    if time_diff > 1800:
                        self.app.job_queue.run_once(self.send_reminder, time_diff - 1800, data={
                            'name': line[0],
                            'time': line[1],
                            'user_id': user,
                            'in': "30 minutes"
                        })

                    # Check if event is 2 hours or more in the future, and add reminder if it is
                    if time_diff > 7200:
                        self.app.job_queue.run_once(self.send_reminder, time_diff - 7200, data={
                            'name': line[0],
                            'time': line[1],
                            'user_id': user,
                            'in': "2 hours"
                        })

                    # Check if event is 1 day or more in the future, and add reminder if it is
                    if time_diff > 86400:
                        self.app.job_queue.run_once(self.send_reminder, time_diff - 86400, data={
                            'name': line[0],
                            'time': line[1],
                            'user_id': user,
                            'in': "1 day"
                        })

                    # Check if event is 1 week or more in the future, and add reminder if it is
                    if time_diff > 604800:
                        self.app.job_queue.run_once(self.send_reminder, time_diff - 604800, data={
                            'name': line[0],
                            'time': line[1],
                            'user_id': user,
                            'in': "1 week"
                        })







b = PersistentBot()
b.start_bot()