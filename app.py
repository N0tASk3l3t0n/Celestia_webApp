#Import Flask, sqlite3, requests, and libraries
from flask import Flask, render_template, request
import sqlite3
import requests

from geopy.geocoders import Nominatim

app = Flask(__name__)

DATABASE = "celestia.db"

geolocator = Nominatim(user_agent="celestia")
