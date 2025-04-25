import os
from dotenv import load_dotenv
import urllib.request
import json
from datetime import datetime
import urllib.parse
from typing import Dict, Any
import ssl
import certifi

# Load environment variables
load_dotenv()

# Get API keys from environment variables
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
MBTA_API_KEY = os.getenv("MBTA_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Useful base URLs (you need to add the appropriate parameters for each API request)
# MAPBOX_BASE_URL = "https://api.mapbox.com/search/searchbox/v1/suggest?q={search_text}""
MAPBOX_BASE_URL = "https://apspi.mapbox.com/geocoding/v5/mapbox.places"
MBTA_BASE_URL = "https://api-v3.mbta.com/stops"
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

def get_json(url: str) -> dict:
    """
    Given a properly formatted URL for a JSON web API request, return a Python JSON object containing the response to that request.
    """
    try:
        # Create a Request object with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        request = urllib.request.Request(url, headers=headers)

        # Use certifi’s certificate bundle for SSL/TLS connections
        context = ssl.create_default_context(cafile=certifi.where())
        
        with urllib.request.urlopen(request, context=context) as f:
            response_text = f.read().decode('utf-8')
            return json.loads(response_text)
    except urllib.error.HTTPError as e:
        print(f'HTTP Error: {e.code} - {e.reason}')
        return {}
    except urllib.error.URLError as e:
        print(f'URL Error: {e.reason}')
        return {}
    except Exception as e:
        print(f'Error fetching data: {e}')
        return {}

def get_lat_lng(place_name: str) -> tuple[str, str, str]:
    """
    Get coordinates and city name for a given place with proper URL encoding
    """
    try:
        # Properly encode the place name for URL
        query = urllib.parse.quote(place_name)
        url = f'{MAPBOX_BASE_URL}/{query}.json?access_token={MAPBOX_TOKEN}&types=place,poi'
        
        data = get_json(url)
        
        if not data or 'features' not in data or not data['features']:
            print(f"No location found for: {place_name}")
            return "Error", "Error", "Error"
            
        feature = data['features'][0]
        longitude, latitude = feature['center']
        
        # Extract city name from context
        city_name = "Unknown"
        context = feature.get("context", [])
        
        # First try to get the place name
        for ctx in context:
            if ctx.get("id", "").startswith("place."):
                city_name = ctx.get("text", "Unknown")
                break
        
        # If no city found in context, use the place name itself
        if city_name == "Unknown" and feature.get("text"):
            city_name = feature.get("text")
                
        return str(latitude), str(longitude), city_name
        
    except Exception as e:
        print(f'Error getting coordinates: {e}')
        return "Error", "Error", "Error"

def get_weather(city_name: str) -> dict:
    """
    Get weather information with proper URL encoding
    """
    try:
        # Properly encode the city name for URL
        encoded_city = urllib.parse.quote(f"{city_name},US")
        url = f"{WEATHER_BASE_URL}?q={encoded_city}&appid={WEATHER_API_KEY}&units=imperial"
        
        data = get_json(url)
        
        if not data or "main" not in data:
            print(f"No weather data found for: {city_name}")
            return {
                "temp": "N/A",
                "condition": "N/A",
                "description": "Weather data unavailable",
                "humidity": "N/A",
                "feels_like": "N/A",
                "wind_speed": "N/A"
            }
            
        return {
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "condition": data["weather"][0]["main"],
            "description": data["weather"][0]["description"].capitalize(),
            "humidity": data["main"]["humidity"],
            "wind_speed": round(data.get("wind", {}).get("speed", 0))
        }
        
    except Exception as e:
        print(f"Error getting weather: {e}")
        return {
            "temp": "Error",
            "condition": "Error",
            "description": "Error",
            "humidity": "Error",
            "feels_like": "Error",
            "wind_speed": "Error"
        }

def get_nearest_station(latitude: str, longitude: str) -> tuple[str, bool]:
    """
    Get nearest MBTA station with proper parameter handling
    """
    try:
        # Ensure parameters are properly formatted
        params = urllib.parse.urlencode({
            'api_key': MBTA_API_KEY,
            'filter[latitude]': latitude,
            'filter[longitude]': longitude,
            'sort': 'distance'
        })
        
        url = f"{MBTA_BASE_URL}?{params}"
        data = get_json(url)
        
        if not data or not data.get('data'):
            print(f"No station found near coordinates: ({latitude}, {longitude})")
            return "No station found", False
        
        station = data['data'][0]
        station_name = station['attributes']['name']
        wheelchair_accessible = bool(station['attributes']['wheelchair_boarding'])
        
        return station_name, wheelchair_accessible
    
    except Exception as e:
        print(f'Error finding nearest station: {e}')
        return 'Error finding station', False

def find_stop_near(place_name: str) -> Dict[str, Any]:
    """
    Process a location search request and return all necessary data for template rendering.
    Handles all business logic including error cases.
    
    Args:
        place_name: Location to search for
        
    Returns:
        Dictionary containing all data needed for template rendering,
        including error message if applicable
    """
    try:
        # Get location coordinates
        latitude, longitude, city_name = get_lat_lng(place_name)
        if latitude == 'Error' or longitude == 'Error':
            return {'error': "Location not found"}
        
        # Get nearest station info
        station_name, wheelchair_accessible = get_nearest_station(latitude, longitude)
        if station_name == 'Error finding station':
            return {'error': "No nearby stations found"}
        # Get weather data
        weather_info = get_weather(city_name)
        if weather_info.get("temp") == "Error":
            return {'error': "Weather data not available"}

        return {
            'place_name':place_name,
            'location':{
                'city':city_name,
                'lat': latitude,
                'lon': longitude
            },
            'station':{
                'name':station_name,
                'wheelchair_accessible': wheelchair_accessible
            },
            'weather': weather_info,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        print(f"Error in find_stop_near:{str(e)}")
        return {'error': f"An error occurred: {str(e)}"}

def display_location_info(location_info: dict) -> None:
    """Helper function to display formatted location, transit, and weather information."""
    
    if 'error' in location_info:
        print(f"\nError: {location_info['error']}")
        return

    print(f"\n{'='*60}")
    print(f"Information for: {location_info['place_name']}")
    print(f"Time: {location_info['timestamp']}")
    print(f"{'='*60}")

    # Display location details
    print(f"\n LOCATION")
    print(f"City: {location_info['location']['city']}")
    print(f"Coordinates: ({location_info['location']['lat']}, {location_info['location']['lon']})")

    # Display station details
    print(f"\n NEAREST MBTA STATION")
    print(f"Station: {location_info['station']['name']}")
    print(f"Wheelchair Accessible: {'✓' if location_info['station']['wheelchair_accessible'] else '✗'}")

    # Display weather details
    weather_info = location_info['weather']
    print(f"\n WEATHER CONDITIONS")
    print(f"Temperature: {weather_info['temp']}°F")
    print(f"Feels Like: {weather_info['feels_like']}°F")
    print(f"Condition: {weather_info['description']}")
    print(f"Humidity: {weather_info['humidity']}%")
    print(f"Wind Speed: {weather_info['wind_speed']} mph")

    print(f"\n{'='*60}")


def main():
    """
    Test all the above functions here.
    """
    test_locations = [
        "Boston College",
        "Harvard University",
        "MIT",
        "Fenway Park",
        "Boston Common"
    ]
    
    print("\nFetching information for various Boston locations...")
    print("Note: This may take a few moments.\n")
    
    for location in test_locations:
        location_info = find_stop_near(location)
        display_location_info(location_info)


if __name__ == "__main__":
    main()