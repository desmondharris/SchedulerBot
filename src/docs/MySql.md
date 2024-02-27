Database: telegram
TABLES:

users:
    chatid: int

events:
    user: int(user.chatid)
    name: str
    datetime: str
        -"YYYY-MM-DD HH:MM"

recurringevents:
    user: int(user.chatid)
    name: str
    recurrence: str
        -"DAY:10:05", "WEEK:Monday", "MONTH:30"
    
    

