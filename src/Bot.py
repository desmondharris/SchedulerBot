import logging

import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from apscheduler.schedulers.blocking import BlockingScheduler
import threading
import asyncio
import datetime
from Calendar import Event, Assignment
import threading
USER_ID = "1710495555"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

'''
Create a telegram bot for scheduling events and assignments.
And then schedule a message to be sent to the user at the specified time using the apscheduler library.
'''


class Bot:
    def __init__(self):
        self.application = ApplicationBuilder().token('6446614126:AAGFL-AP_8BEMRtJ2DUiDR3vR5EWcq-csTI').build()
        self.event_queue = []
        self.event_assignment_queue = []
        self.to_do_list = []
        self.scheduler = BlockingScheduler()

        # Create a text file to store all the events
        self.event_file = open('events.txt', 'w+')
        self.event_file.close()

        # Create a text file to store the to-do list
        self.to_do_file = open('to_do.txt', 'w+')
        self.to_do_file.close()

    def start_scheduler(self):
        self.scheduler.start()
        print('Scheduler started.')

    async def event_message_generator(self, context: telegram.ext.CallbackContext) -> None:
        # Remove the event from the text file
        with open("events.txt", "r+") as f:
            d = f.readlines()
            f.seek(0)
            for i in d:
                if i != f'{context.job.data["event"].title} at {context.job.data["event"].time}\n':
                    f.write(i)
            f.truncate()

        # Send a message with the telegram bot
        time = context.job.data['time']
        title = context.job.data['title']
        await self.application.bot.send_message(chat_id=USER_ID, text='Don\'t forget! ' + title + ' at ' + str(time))

    async def reminder_generator(self, context: telegram.ext.CallbackContext):
        # Send a message with the telegram bot
        title = context.job.data['title']
        time_type = context.job.data['time_type']
        difference = context.job.data['difference']

        await self.application.bot.send_message(chat_id=USER_ID, text=f'Don\'t forget!{title} in {difference} {time_type}!')

    async def add_to_do(self, update: Update, context: telegram.ext.CallbackContext) -> None:
        # Get the message, and remove the command at the beginning
        message = update.message.text[6:]
        # Add the message to the to do list
        self.to_do_list.append(message)
        # Send a message to the user confirming that the message has been added to the to do list
        await self.application.bot.send_message(chat_id=USER_ID, text=f'To do item {message} has been added to the to do list.')

    async def get_to_do_list(self, update: Update, context: telegram.ext.CallbackContext) -> None:
        # Create neat to do list, with one item on each line
        msg = '\n'.join(self.to_do_list)

        # Send a message to the user with the to do list
        await self.application.bot.send_message(chat_id=USER_ID, text=f'Your to do list:\n {msg}')

    async def add_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        new_event = Event(update.message.text)
        print("Event added: ", new_event.title, " at ", new_event.time)

        # Calculate the time difference between now and the event time
        time_difference = new_event.time - new_event.time_created
        # Convert the time difference to seconds
        time_difference_seconds = time_difference.total_seconds()
        print(time_difference_seconds)

        # Check if event is in the past
        if time_difference_seconds < 0:
            await self.application.bot.send_message(chat_id=USER_ID, text=f'Event {new_event.title} at {new_event.time} has already passed.')
            return

        # Add the event to the queue and text file
        self.application.job_queue.run_once(self.event_message_generator, time_difference_seconds, data={
            'event': new_event,
            'time': new_event.time,
            'title': new_event.title
        })

        self.event_queue.append(new_event)
        self.event_file = open('events.txt', 'a')
        self.event_file.write(f'{new_event.title} at {new_event.time}\n')
        self.event_file.close()

        await self.application.bot.send_message(chat_id=USER_ID, text=f'Reminder for event {new_event.title} at {new_event.time} has been set.')

        # Check to see if there are 30 minutes between now and event time.
        if time_difference_seconds < 1800:
            return
        # Add job to remind user 30 minutes before event
        self.application.job_queue.run_once(self.event_message_generator, time_difference_seconds - 1800, data={
            'title': new_event.title,
            'time_type': 'minutes',
            'difference': 30
        })

        # Check to see if there are 2 hours between now and event time.
        if time_difference_seconds < 7200:
            return
        # Add job to remind user 2 hours before event
        self.application.job_queue.run_once(self.event_message_generator, time_difference_seconds - 7200, data={
            'title': new_event.title,
            'time_type': 'hours',
            'difference': 2
        })

        # Check to see if there are 1 day between now and event time.
        if time_difference_seconds < 86400:
            return
        # Add job to remind user 1 day before event
        self.application.job_queue.run_once(self.event_message_generator, time_difference_seconds - 86400, data={
            'title': new_event.title,
            'time_type': 'days',
            'difference': 1
        })

        # Check to see if there are 3 days between now and event time.
        if time_difference_seconds < 259200:
            return
        # Add job to remind user 3 days before event
        self.application.job_queue.run_once(self.event_message_generator, time_difference_seconds - 259200, data={
            'title': new_event.title,
            'time_type': 'days',
            'difference': 3
        })

        # Check to see if there are 7 days between now and event time.
        if time_difference_seconds < 604800:
            return
        # Add job to remind user 7 days before event
        self.application.job_queue.run_once(self.event_message_generator, time_difference_seconds - 604800, data={
            'title': new_event.title,
            'time_type': 'week',
            'difference': 1
        })


    async def daily_reminders(self):
        daily_reminder = "Good morning! Here's your schedule for today: \n"
        for event in self.event_queue:
            # Check if event is today
            if event.time.date() == datetime.datetime.now().date():
                daily_reminder += f'{event.title} at {event.time}\n'
        await self.application.bot.send_message(chat_id=USER_ID, text=daily_reminder)



    def run_bot(self):
        # Add handlers here
        add_event_handler = CommandHandler('addevent', self.add_event)
        self.application.add_handler(add_event_handler)

        # Add todo handler
        add_todo_handler = CommandHandler('todo', self.add_to_do)
        self.application.add_handler(add_todo_handler)

        # Add todolist handler
        todo_list_handler = CommandHandler('todolist', self.get_to_do_list)
        self.application.add_handler(todo_list_handler)

        # Add daily reminder handler


        # Start the bot
        print('Starting bot thread...')
        self.application.run_polling()

