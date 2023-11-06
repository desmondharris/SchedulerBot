import datetime
from Core import *

class Event:
    def convert_time(self):
            month_to_number = {
                'January': 1,
                'February': 2,
                'March': 3,
                'April': 4,
                'May': 5,
                'June': 6,
                'July': 7,
                'August': 8,
                'September': 9,
                'October': 10,
                'November': 11,
                'December': 12
            }
            split_msg = self.time_unf.split(maxsplit=5)[1:]
            self.time = datetime.datetime(int(split_msg[2]), month_to_number[split_msg[0]], int(split_msg[1]), time_convert(split_msg[3])[0], time_convert(split_msg[3])[1])
            self.title = split_msg[4]

    def __init__(self, start_message, location=None):
        self.time = None
        self.title = None
        self.time_created = datetime.datetime.now()
        self.time_unf = start_message
        if location:
            self.location = location

        self.convert_time()


class Assignment:
    #def convert_due_date(self):

    def __init__(self, due_date, title, course):
        self.time = None

        self.date_created = datetime.time()
        self.time_unf = due_date



