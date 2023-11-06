import datetime
from typing import Tuple, Type


def time_convert(time_raw: str) -> tuple:
    time_split = time_raw.split(':')
    hours = int(time_split[0])
    mins = int(time_split[1][:2])

    if time_split[1][2:] == 'pm':
        hours += 12

    return hours, mins


def convert_event_message_to_time(event_message: str):
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

        '''
        /addevent Brown Fellows Meeting on October 31 2023  
        '''
        split_msg = event_message.split(maxsplit=5)[1:]
        time = datetime.datetime(int(split_msg[2]), month_to_number[split_msg[0]], int(split_msg[1]), time_convert(split_msg[3])[0], time_convert(split_msg[3])[1])
        title: str = split_msg[4]
        return title, time


