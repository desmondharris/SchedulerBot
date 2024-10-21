from telegram import InlineKeyboardButton, InlineKeyboardMarkup
FIRST_TIME_GREETING = "Welcome to the bot!"
START_HELP_MESSAGE = "REPLACEME Help Message"
WEEKDAY_INLINE_TEXT = "Reminders?"
WEEKDAY_INLINE_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("5 Minutes", callback_data="5-minutes"),
     InlineKeyboardButton("15 Minutes", callback_data="15-minutes"),
     InlineKeyboardButton("30 Minutes", callback_data="30-minutes")],
    [InlineKeyboardButton("1 Hour", callback_data="1-hours"),
        InlineKeyboardButton("2 Hours", callback_data="2-hours"),
        InlineKeyboardButton("1 day", callback_data="4-hours")],
])
