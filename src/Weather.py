"""
Handles calls to the OpenWeatherMap API
"""
from bs4 import BeautifulSoup
import requests

from Keys import WEATHER_API_KEY


def get_weather(api_key, city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=imperial"
    response = requests.get(url)
    if response.status_code == 200:
        w_dict = response.json()
        return w_dict
    else:
        return f"Error: {response.status_code}"


print(get_weather(WEATHER_API_KEY, "Louisville"))
