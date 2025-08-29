import re
import requests
import os
from logger import logger

WEATHER_API_KEY = 'fba556754e99150c7552df66ac2b6f29'
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

def extract_city(text: str) -> str:
    """
    Extract a clean city name from user text.
    Removes words like 'weather', 'the', and non-letter characters.
    """
    # Lowercase for consistent processing
    text = text.lower()
    
    # Remove keywords that are not part of the city
    text = re.sub(r'\b(weather|in|what\'s|tell me|the)\b', '', text, flags=re.IGNORECASE)
    
    # Remove non-letter characters
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    # Strip extra spaces
    city = text.strip()
    
    # Title case for API compatibility
    return city.title()


def get_weather(city: str) -> str:
    """
    Fetch weather information from OpenWeatherMap for the given city.
    Returns a user-friendly message or error.
    """
    if not WEATHER_API_KEY:
        return "❌ Weather API key not found. Please check your .env file."

    if not city:
        return "❌ Could not extract city name."

    try:
        params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric"}
        res = requests.get(WEATHER_URL, params=params)
        res.raise_for_status()
        data = res.json()

        desc = data["weather"][0]["description"].capitalize()
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        return f"🌦️ The weather in {city} is {desc} with {temp}°C (feels like {feels}°C)."
    except requests.HTTPError as e:
        if res.status_code == 401:
            return "❌ Invalid Weather API key. Please check your .env file."
        elif res.status_code == 404:
            return f"❌ City '{city}' not found."
        else:
            return f"❌ Couldn't fetch weather for {city}. ({e})"
    except Exception as e:
        return f"❌ Error fetching weather: {e}"


print(get_weather("New York"))