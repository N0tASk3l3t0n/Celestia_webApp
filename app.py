#Import Flask, sqlite3, requests, and libraries
from flask import Flask, render_template, request
import sqlite3
import requests
from skyfield.api import load, Topos, utc
from skyfield.framelib import ecliptic_frame
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

DATABASE = "celestia.db"

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





#------------
#App Routing
#------------

#Home Route
@app.route("/")
def home():
    return render_template("index.html")


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

    return render_template(
        "details.html",
        city=city,
        latitude=lat,
        longitude=lon,
        date=date,
        time=time,
        planets=planets

    )

#Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)