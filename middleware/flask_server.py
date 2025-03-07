# hosts the middleware for a civic server
# hosts a REST API for internal_clients to communicate with via flask (send data, get data, etc)
# handles model updates
# handles model deletions
# hosts model downloads
# keeps track of connected internal_clients
# stores data in postgres database

import os
import json
from waitress import serve
from flask import Flask, Response, jsonify
from flask_cors import CORS, cross_origin
import logging
import psycopg2
from psycopg2 import sql
import signal
import sys

app = Flask(__name__)
CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

logging.basicConfig(level=logging.DEBUG)

db = None


@app.route("/")
@cross_origin()
def health_check():
    return "200 OK"


@app.route("/get_models", methods=["GET"])
@cross_origin()
def get_models():
    return db_query("SELECT * FROM models")


def conn_db():
    global db
    db = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "civic_db"),
        user=os.getenv("POSTGRES_USER", "civic_db_admin"),
        password="passwd",
        host=os.getenv("POSTGRES_HOST", "civic-db"),
        port=os.getenv("POSTGRES_PORT", "5432"),
    )


def db_query(query):
    # Create db cursor
    cur = db.cursor()

    # Execute query
    app.logger.info(f"Executing query: {query}")
    cur.execute(query)
    col_names = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    # Close cursor
    cur.close()

    # Combine column names and rows into a list of dicts
    result = []
    for row in rows:
        result.append(dict(zip(col_names, row)))

    # Return result
    result = json.dumps(result, sort_keys=False)
    app.logger.info(f"Query result: {result}")
    return Response(result, mimetype="application/json")


def safe_exit(*args):
    if db:
        db.close()
    app.logger.info("Exiting...")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, safe_exit)
    signal.signal(signal.SIGTERM, safe_exit)

    conn_db()
    serve(app, host="0.0.0.0", port=5000)
