import logging

import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import schedule
import datetime
from Calendar import Event
from Keys import TELEGRAM_API_KEY, TELEGRAM_USER_ID, WEATHER_API_KEY
import requests, json


USER_ID = TELEGRAM_USER_ID


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

'''
Create a telegram bot for scheduling events and assignments.
And then schedule a message to be sent to the user at the specified time using the apscheduler library.
'''


'''
Create a function that converts a string like this:
Brown at 2023-10-31 20:00:00
into an event object.
'''
def string_to_event(string: str) -> Event:
    # Split the string into two parts
    string_parts = string.split(' at ')
    # Get the title
    title = string_parts[0]
    # Get the time
    time = datetime.datetime.strptime(string_parts[1], '%Y-%m-%d %H:%M:%S')
    # Create a new event object
    new_event = Event(title, time)
    return new_event


def city_name_to_lat_long(city_name: str, limit: int, state: str) -> tuple:
    cities = requests.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit={limit}&appid={WEATHER_API_KEY}").json()
    for city in cities:
        if city['state'] == state:
            return city['lat'], city['lon']


def get_weather(city: str, state: str, limit: int) -> str:
    ret = ""
    lat, lon = city_name_to_lat_long(city, limit, state)
    weather = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}").json()
    weather = weather['main']
    weather['temp'] = round(weather['temp']*9/5 - 459.67)
    weather['feels_like'] = round(weather['feels_like']*9/5 - 459.67)
    weather['temp_min'] = round(weather['temp_min']*9/5 - 459.67)
    weather['temp_max'] = round(weather['temp_max']*9/5 - 459.67)
    return weather

class Bot:
    def __init__(self):
        self.application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()
        self.event_queue = []
        self.event_assignment_queue = []
        self.to_do_list = []

        # Create a text file to store all the events
        self.event_file = open('events.txt', 'w+')
        self.event_file.close()

        # Create a text file to store the to-do list
        self.to_do_file = open('to_do.txt', 'w+')
        self.to_do_file.close()

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


    async def daily_reminders(self, context: telegram.ext.CallbackContext):
        print('Sending daily reminders...')
        weather_info = get_weather('Louisville', 'Kentucky', 10)
        daily_reminder = (f"Good morning! The temperature is {weather_info['temp']} and feels like "
                          f"{weather_info['feels_like']}. The high today is {weather_info['temp_max']}, with a low of "
                          f"{weather_info['temp_min']}. The humidity is {weather_info['humidity']}.\n")

        daily_reminder += "Here's your schedule for today: \n"
        for event in self.event_queue:
            # Check if event is today
            if event.time.date() == datetime.datetime.now().date():
                daily_reminder += f'{event.title} at {event.time}\n'

        # Add to do list
        daily_reminder += "\nHere's your current to do list: \n"
        for item in self.to_do_list:
            daily_reminder += f'{item}\n'

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

        # Start the scheduler
        self.application.job_queue.run_daily(self.daily_reminders, datetime.time(hour=8, minute=0, second=0))


        # Start the bot
        print('Starting bot thread...')
        try:
            self.application.run_polling()
        except KeyboardInterrupt:
            print('Stopping bot...')


bot = Bot()
bot.run_bot()

