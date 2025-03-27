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
from flask import Flask, Response, request
from flask_cors import CORS, cross_origin
import logging
import psycopg2

# from psycopg2 import sql
import signal
import sys
import random

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


@app.route("/clients", methods=["POST"])
@cross_origin()
def add_client():
    return db_query(
        "INSERT INTO clients (ip, port, status) VALUES ('%s', '%s', 1) RETURNING *;"
        % (request.json.get("ip"), request.json.get("port"))
    )


@app.route("/clients/<client_uuid>/deactivate", methods=["PUT"])
@cross_origin()
def deactivate_client(client_uuid):
    return db_query(
        "UPDATE clients SET status = 0 WHERE client_uuid = '%s' RETURNING *;"
        % client_uuid
    )


@app.route("/clients/<client_uuid>/activate", methods=["PUT"])
@cross_origin()
def activate_client(client_uuid):
    return db_query(
        "UPDATE clients SET status = 1 WHERE client_uuid = '%s' RETURNING *;"
        % client_uuid
    )


@app.route("/download_binary/<int:model_id>", methods=["GET"])
@cross_origin()
def download_binary(model_id):
    query = f"SELECT binary_data FROM model_binaries WHERE model_id = {model_id} ORDER BY version DESC LIMIT 1;"
    cur = db.cursor()
    app.logger.info(f"Executing query: {query}")
    cur.execute(query)
    binary_data = cur.fetchone()
    cur.close()

    if binary_data:
        return Response(binary_data[0], mimetype="application/octet-stream")
    else:
        return Response("Binary not found", status=404)


@app.route("/dataset/<int:model_id>", methods=["GET"])
@cross_origin()
def get_dataset(model_id):
    query = f"SELECT * FROM model_{model_id}_data;"
    return db_query(query)


@app.route("/create_dataset/<int:model_id>", methods=["POST"])
@cross_origin()
def create_dataset(model_id):
    try:
        # Parse the request data
        dataset_type = request.json.get("type")
        data = request.json.get("data")
        split = int(request.json.get("split", 5))
        replication = request.json.get("replication", False)
        replication_percentage = int(request.json.get("replication_percentage", 10))
        shuffle = request.json.get("shuffle", False)

        if not dataset_type or not data:
            return Response("Invalid dataset payload", status=400)

        # Shuffle the dataset if required
        if shuffle:
            random.shuffle(data)

        # Split the dataset
        splits = [data[i : i + split] for i in range(0, len(data), split)]

        # Handle replication if enabled
        if replication:
            replication_count = max(1, (len(splits) * replication_percentage) // 100)
            replicated_splits = random.sample(splits, replication_count)
            splits.extend(replicated_splits)

        # Define the table name
        table_name = f"model_{model_id}_data"
        # Create a cursor
        cur = db.cursor()
        # Check if the table has existing data and delete it (user chose to overwrite)
        cur.execute(f"DELETE FROM {table_name};")

        # Insert the dataset into the table
        for split_index, split_data in enumerate(splits):
            cur.execute(
                f"INSERT INTO {table_name} (model_id, data) VALUES (%s, %s);",
                (model_id, json.dumps(split_data)),
            )

        db.commit()
        cur.close()

        return Response("Dataset created successfully", status=201)
    except Exception as e:
        app.logger.error(f"Error creating dataset: {e}")
        return Response(f"Error creating dataset: {e}", status=500)


@app.route("/clients", methods=["GET"])
@cross_origin()
def get_clients():
    return db_query("SELECT * FROM clients")


@app.route("/results/<int:model_id>", methods=["GET"])
@cross_origin()
def get_results(model_id):
    query = f"SELECT * FROM model_{model_id}_results;"
    return db_query(query)


@app.route("/upload_result/<int:model_id>", methods=["POST"])
@cross_origin()
def upload_result(model_id):
    # Parse the request data
    try:
        client_uuid = request.json.get("client_uuid")
        data_split_id = request.json.get("id")
        result_data = request.json.get("data")

        if not result_data or not client_uuid:
            return Response("Invalid result payload", status=400)

        # Define the table name
        table_name = f"model_{model_id}_results"

        # Insert the result into the table
        cur = db.cursor()
        cur.execute(
            f"INSERT INTO {table_name} (data_split_id, model_id, client_uuid, result) VALUES (%s, %s, %s, %s);",
            (data_split_id, model_id, client_uuid, json.dumps(result_data)),
        )
        db.commit()
        cur.close()

        return Response("Result uploaded successfully", status=201)
    except Exception as e:
        app.logger.error(f"Error uploading result: {e}")
        return Response(f"Error uploading result: {e}", status=500)


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
    global db

    # Create db cursor
    cur = db.cursor()

    # Execute query
    app.logger.info(f"Executing query: {query}")
    cur.execute(query)
    col_names = [desc[0] for desc in cur.description] if cur.description else []
    rows = cur.fetchall() if cur.description else []

    # Close cursor
    cur.close()

    # Commit the transaction
    db.commit()

    # Combine column names and rows into a list of dicts
    result = []
    for row in rows:
        result.append(dict(zip(col_names, row)))

    # Return result
    result = json.dumps(result, sort_keys=False, default=str)
    app.logger.info(f"Query result: {result}")
    return Response(result, mimetype="application/json")


def safe_exit(*_):
    if db:
        db.close()
    app.logger.info("Exiting...")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, safe_exit)
    signal.signal(signal.SIGTERM, safe_exit)

    conn_db()
    serve(app, host="0.0.0.0", port=5000)
