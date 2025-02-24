# hosts the middleware for a civic server
# hosts a REST API for internal_clients to communicate with via flask (send data, get data, etc)
# handles model updates
# handles model deletions
# hosts model downloads
# keeps track of connected internal_clients
# stores data in postgres database

import os
import requests
import docker
import time
import json

from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app)
app.config('CORS_HEADERS') = 'Content-Type'

@app.route("/")
@cross_origin()
def health_check():
  return "200 OK"

