#Import Flask, sqlite3, requests, and libraries
from flask import Flask, render_template, request
import sqlite3
import requests
from skyfield.api import load, Topos, utc
from datetime import datetime
NASA_API_KEY = "oMEgevkHMrRxKjC6g06pJ4Zfyhl94u7TxWUVCmfr"

from geopy.geocoders import Nominatim

app = Flask(__name__)

#----------------------------
#Skyfield Setup - Planet Data
#----------------------------
#Load Skyfield Data 
ts = load.timescale()

#Downloads de421.bsp - all data for the planets in the solar system
planets = load('de421.bsp')

earth = planets['earth']
sun = planets ['sun']

DATABASE = "planets.db"

geolocator = Nominatim(user_agent="celestia")


#Create the function for geolocation to get the latitude and longitude of the city entered by the user
def get_coordinates(city):
    location = geolocator.geocode(city)

    if location:
        return location.latitude, location.longitude
    return None, None

#Planet function for planet data to present in the details.html file
def get_visible_planets(lat, lon, date, time):
    observer = earth + Topos(latitude_degrees=float(lat), longitude_degrees=float(lon))

    dt = datetime.strptime(
         f"{date} {time}",
        "%Y-%m-%d %H:%M"
    )

    dt = dt.replace(tzinfo=utc)

    t = ts.from_datetime(dt)

    planet_names = [
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter barycenter",
        "Saturn barycenter",
        "Uranus barycenter",
        "Neptune barycenter"
    ]

    results = []
    for name in planet_names:
        planet = planets[name]

        astrometric = observer.at(t).observe(planet)

        apparent = astrometric.apparent()

        alt, az, distance = apparent.altaz()

        #Is the planet Visible
        visible = alt.degrees > 0

        results.append({

            "name": name.replace(" barycenter", ""),

            "visible": visible,

            "altitude": round(alt.degrees, 2),

            "azimuth": round(az.degrees, 2),

            "distance": round(distance.au, 3)
        })

    return results

#------------------------------------------------------------------------------
#Open Meteo - Weather API get weather data for the given latitude and longitude
#------------------------------------------------------------------------------
def get_weather(lat, lon):
    url = url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&current=temperature_2m,cloud_cover"
    )

    response = requests.get(url)
    data = response.json()

    return {
        "temperature": data["current"]["temperature_2m"],

        "cloud_cover": data["current"]["cloud_cover"]
    }

#--------------------------------------------------------
#NASA Image of the Day API for use in the index.html file 
#--------------------------------------------------------
def get_apod():
    url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    return {
        "title": data.get("title"),
        "date": data.get("date"),
        "image":data.get("url"),
        "explanation": data.get("explanation"),
        "copyright": data.get("copyright", "NASA")
    }

#---------------------------
#Cloud Cover Rating Function returns a rating based on cloud cover percentage
#---------------------------
def viewing_rating(cloud_cover):
    if cloud_cover < 20:
        return "Excellent"
    elif cloud_cover < 40:
        return "Good"
    elif cloud_cover < 60:
        return "Fair"
    elif cloud_cover < 80:
        return "Poor"
    else:
        return "Very Poor"

#---------------
#Database Setup for Search History
#---------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

#Create the search history table
def create_tables():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS searches (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            city TEXT,

            latitude REAL,

            longitude REAL,

            search_date TEXT,

            search_time TEXT,

            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    conn.commit()
    conn.close()

#Save search history to the database
def save_search(city, lat, lon, date, time):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO searches
        (city, latitude, longitude, search_date, search_time)
        VALUES (?, ?, ?, ?, ?)
    """, (city, lat, lon, date, time))
    conn.commit()
    conn.close()

#Get search history
def get_search_history():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM searches
        ORDER BY searched_at DESC
    """)
    history = cursor.fetchall()
    conn.close()
    return history 

#------------
#App Routing - Includes Home, Details, and History Routes
#------------

#Home Route to Index.html file (MAIN PAGE)
@app.route("/")
def home():
    history = get_search_history()
    apod = get_apod()
    return render_template("index.html", history=history, apod=apod)

#Route to Details.html file (RESULTS PAGE)
@app.route("/details", methods=["POST"])
def details():
    city = request.form.get("city")
    date = request.form.get("date")
    time = request.form.get("time")
    lat = request.form.get("lat")
    lon = request.form.get("lng")

    if city:
        lat, lon = get_coordinates(city)

    
    elif not lat or not lon:
        return render_template("index.html", error="City not found")

    planets = get_visible_planets(lat, lon, date, time)
    weather = get_weather(lat, lon)
    weather["rating"] = viewing_rating(weather["cloud_cover"])
    save_search(city, lat, lon, date, time)

    return render_template(
        "details.html",
        city=city,
        latitude=lat,
        longitude=lon,
        date=date,
        time=time,
        planets=planets,
        weather=weather

    )
#Search History Route to history.html file (SEARCH HISTORY PAGE)
@app.route("/history")
def history():

    searches = get_search_history()
    return render_template("history.html", searches=searches)


#Run the Flask app
if __name__ == "__main__":
    create_tables()
    app.run(debug=True)