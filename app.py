#Import Flask, sqlite3, requests, and libraries
from flask import Flask, render_template, request
import sqlite3
import requests
from skyfield.api import load, Topos, utc
from datetime import datetime

from geopy.geocoders import Nominatim

app = Flask(__name__)

#-----------------
#Skyfield Setup
#-----------------
#Load Skyfield Data
ts = load.timescale()

#Downloads de421.bsp
planets = load('de421.bsp')

earth = planets['earth']
sun = planets ['sun']

DATABASE = "planets.db"

geolocator = Nominatim(user_agent="celestia")


#Create the function for geolocation
def get_coordinates(city):
    location = geolocator.geocode(city)

    if location:
        return location.latitude, location.longitude
    return None, None

#Planet function for planets
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

#------------------------
#Open Meteo - Weather API 
#------------------------
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

#---------------------------
#Cloud Cover Rating Function
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
#Database Setup
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

#Save search
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
#App Routing
#------------

#Home Route
@app.route("/")
def home():
    history = get_search_history()
    return render_template("index.html", history=history)


@app.route("/details", methods=["POST"])
def details():
    city = request.form.get("city")
    date = request.form.get("date")
    time = request.form.get("time")
    lat = request.form.get("lat")
    lon = request.form.get("lng")

    if city:
        lat, lon = get_coordinates(city)

    
    elif lat is None or lon is None:
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
#Search History Route
@app.route("/history")
def history():

    searches = get_search_history()
    return render_template("history.html", searches=searches)


#Run the Flask app
if __name__ == "__main__":
    create_tables()
    app.run(debug=True)