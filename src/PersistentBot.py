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
        add_handler = ConversationHandler(
            entry_points=[CommandHandler("add", self.add)],
            states={
                'event': [MessageHandler(filters.TEXT, self.event_get_date)],
                'switch': [
                    MessageHandler(
                        filters.Regex("^Event$"), self.event_get_date
                    ),
                    MessageHandler(
                        filters.Regex("^Recurring Event$"), self.reccuring_event_get_frequency
                    ),
                ],
                'event_get_date': [MessageHandler(filters.TEXT, self.event_get_date)],
                'event_get_time': [MessageHandler(filters.TEXT, self.event_get_time)],
                'event_get_name': [MessageHandler(filters.TEXT, self.event_get_name)],
                'event_finish': [MessageHandler(filters.TEXT, self.event_finish)],
                'recurring_event_process_frequency': [MessageHandler(filters.TEXT, self.reccuring_event_process_frequency)],
                'recurring_event_get_time': [MessageHandler(filters.TEXT, self.reccuring_event_get_time)],
                'recurring_event_get_name': [MessageHandler(filters.TEXT, self.reccuring_event_get_name)],
                'recurring_event_finish': [MessageHandler(filters.TEXT, self.reccuring_event_finish)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        self.app.add_handler(add_handler)
        #self.build_from_old()

    def start_bot(self):
        self.app.run_polling()

    async def reccuring_event_get_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Get the date of the event
        """
        await update.message.reply_text("How often should the event happen? Enter something like:\n1 days\n2 weeks\n3 months\n(MUST BE PLURAL)")
        return "recurring_event_process_frequency"

    async def reccuring_event_process_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        frequency, time_period = update.message.text.split(' ')
        frequency = int(frequency)
        time_period = time_period.lower()
        context.user_data["frequency"] = frequency
        context.user_data["time_period"] = time_period

        if time_period == "days":
            await update.message.reply_text("What day of the week should the event start? (Monday, Tuesday, etc.)")
            return "recurring_event_get_time"
        elif time_period == "weeks":
            await update.message.reply_text("What day(s) of the week should the event occur?\nTo enter multiple days, separate them with a comma and a space (Monday, Tuesday, etc.)")
        elif time_period == "months":
            await update.message.reply_text("What day of the month should the event occur? (1, 2, 3, etc.)")

        return "recurring_event_get_time"

    async def reccuring_event_get_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        time_period = context.user_data["time_period"]
        day_to_num = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6
        }

        if time_period == "days":
            day = update.message.text.lower()
            day = day_to_num[day]
            context.user_data["day"] = day
        elif time_period == "weeks":
            days = update.message.text.split(', ')
            days = [day_to_num[day.lower()] for day in days]
            context.user_data["days"] = days
        elif time_period == "months":
            day = int(update.message.text)
            context.user_data["day"] = day

        await update.message.reply_text("When is the event? (HH:MM)")
        return "recurring_event_get_name"

    async def reccuring_event_get_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Get the name of the event
        """
        time = update.message.text

        # Create time object
        time = datetime.datetime.strptime(time, "%H:%M").time()
        context.user_data["time"] = time

        await update.message.reply_text("What is the name of the event?")
        return "recurring_event_finish"

    async def reccuring_event_finish(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = update.message.text
        time_period = context.user_data["time_period"]
        frequency = context.user_data["frequency"]

        if time_period == "days":
            day = context.user_data["day"]
            # Create datetime object of next occurence of this day
            now = datetime.datetime.now()
            next_day = now + datetime.timedelta(days=(day - now.weekday()) % 7)
            # Set time of next occurence to the time the user specified
            next_day = next_day.replace(hour=context.user_data["time"].hour, minute=context.user_data["time"].minute)

            self.app.job_queue.run_repeating(self.send_event, datetime.timedelta(days=frequency), first=next_day, data={
                'name': name,
                'time': next_day,
                'user_id': update.message.chat_id
            })
        elif time_period == "weeks":
            self.app.job_queue.run_daily(self.send_event, context.user_data["time"], days=context.user_data["days"], data={
                'name': name,
                'time': context.user_data["time"],
                'user_id': update.message.chat_id
            })
        elif time_period == "months":
            self.app.job_queue.run_monthly(self.send_event, context.user_data["time"], day=context.user_data["day"], data={
                'name': name,
                'time': context.user_data["time"],
                'user_id': update.message.chat_id
            })

        # Add event to user's recurring events
        user_dir = os.path.join(self.user_dir, str(update.message.chat_id))
        os.mkdir(user_dir) if not os.path.exists(user_dir) else None
        #TODO: add recurring events to user/user_id/recurring_events.txt
        # Create new JSON

        with open(os.path.join(user_dir, f"recurring_events{len(self.recurring_event_queue)}"), "a") as f:
            pass
        return ConversationHandler.END

    # When user types /add, start a conversation
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
            await update.message.reply_text("Event is in the past, cannot add.")
            return ConversationHandler.END



        # Create new JSON
        json_data = {
            "name": name,
            "time": str(context.user_data["time"]),
            "user_id": context.user_data["user_id"],
            "reminders": {
                "30 minutes": time_diff > 1800,
                "2 hours": time_diff > 7200,
                "1 days": time_diff > 86400,
                "1 weeks": time_diff > 604800
            }
        }
        self.set_event_reminders(json_data)

        # Add event to user's events folder
        with open(os.path.join(self.user_dir, str(update.message.chat_id), f"event{context.user_data['name']}{len(self.basic_event_queue)}.json"), "w") as f:
            json.dump(json_data, f)
        self.basic_event_queue.append(json_data)

        # Add event to job queue
        self.app.job_queue.run_once(self.send_event, context.user_data["time"], data={
            'name': name,
            'time': context.user_data["time"],
            'user_id': update.message.chat_id
        })
        return ConversationHandler.END

    def set_event_reminders(self, event: dict):
        for reminder, should_send in event["reminders"].items():
            if should_send:
                # Create a datetime object of the time to run the reminder
                # event["time"] is in the format "30 days", "2 hours", etc.
                splt_time = reminder.split()
                kwargs = {splt_time[1]: int(splt_time[0])}
                time_to_run = datetime.timedelta(**kwargs)
                self.app.job_queue.run_once(self.send_reminder, time_to_run, data={
                    'name': event["name"],
                    'time': event["time"],
                    'user_id': event["user_id"],
                    'in': reminder
                })

    async def send_event(self, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(chat_id=context.job.data["user_id"], text=f"Event: {context.job.data['name']} at {context.job.data['time']}")

    async def send_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        await self.app.bot.send_message(chat_id=context.job.data["user_id"], text=f"Reminder: {context.job.data['name']} in {context.job.data['in']} at {context.job.data['time']}")

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