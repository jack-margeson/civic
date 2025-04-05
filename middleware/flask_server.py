# hosts the middleware for a civic server
# hosts a REST API for internal_clients to communicate with via flask (send data, get data, etc)
# handles model updates
# handles model deletions
# hosts model downloads
# keeps track of connected internal_clients
# stores data in postgres database

import base64
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


@app.route("/get_model/<int:model_id>", methods=["GET"])
@cross_origin()
def get_model(model_id):
    return db_query("SELECT * FROM models WHERE model_id = %s;" % model_id)


@app.route("/edit_model/<int:model_id>", methods=["PUT"])
@cross_origin()
def edit_model(model_id):
    # Parse request data
    model_name = request.json.get("name")
    model_display_name = request.json.get("display_name")
    model_description = request.json.get("description")

    if not model_name or not model_display_name or not model_description:
        return Response("Invalid model payload", status=400)

    # Update the model in the database
    query = f"""
        UPDATE models
        SET name = '{model_name}', display_name = '{model_display_name}', description = '{model_description}'
        WHERE model_id = {model_id}
        RETURNING *;
    """
    return db_query(query)


@app.route("/change_model_status/<int:model_id>", methods=["PUT"])
@cross_origin()
def change_model_status(model_id):
    # Parse request data
    status = request.json.get("status")

    if status not in [0, 1]:
        return Response("Invalid status payload", status=400)

    # Update the model in the database
    query = f"""
        UPDATE models
        SET status = {status}
        WHERE model_id = {model_id}
        RETURNING *;
    """
    return db_query(query)


@app.route("/get_model_binaries/<int:model_id>", methods=["GET"])
@cross_origin()
def get_model_binaries(model_id):
    # Get all binaries for the model
    query = (
        f"SELECT * FROM model_binaries WHERE model_id = {model_id} ORDER BY version;"
    )
    return db_query(query)


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


@app.route("/create_model", methods=["POST"])
@cross_origin()
def create_model():
    try:
        # Parse request data
        model_name = request.json.get("name")
        model_display_name = request.json.get("name")
        model_description = request.json.get("description")

        if not model_name or not model_display_name or not model_description:
            return Response("Invalid model payload", status=400)

        # Get the next model_id
        cur = db.cursor()
        cur.execute("SELECT MAX(model_id) FROM models;")
        max_model_id = cur.fetchone()[0]
        if max_model_id is None:
            max_model_id = 0
        model_id = max_model_id + 1

        # Insert the model into the database
        cur.execute(
            "INSERT INTO models (model_id, name, display_name, description) VALUES (%s, %s, %s, %s) RETURNING model_id;",
            (model_id, model_name, model_display_name, model_description),
        )
        model_id = cur.fetchone()[0]
        app.logger.info(f"Model created with ID: {model_id}")

        # Get JSON representation of the model
        cur.execute(f"SELECT json_agg(models) FROM models WHERE model_id = {model_id};")
        response = cur.fetchone()[0]

        db.commit()
        cur.close()

        app.logger.info(f"Model response: {response}")
        return Response(
            json.dumps(response[0], default=str),
            mimetype="application/json",
            status=201,
        )
    except Exception as e:
        app.logger.error(f"Error creating model: {e}")
        return Response("Invalid model payload", status=400)


@app.route("/upload_model_binary/<int:model_id>", methods=["POST"])
@cross_origin()
def upload_binary(model_id):
    # Parse the request data
    try:
        version = request.json.get("version")
        encoded_data = request.json.get("encoded_data")

        if not encoded_data:
            return Response("Invalid binary payload", status=400)

        app.logger.info(f"{encoded_data}")
        # Convert binary data in base64 to bytes
        binary_data = base64.b64decode(encoded_data)

        # Insert into model_binaries table
        cur = db.cursor()
        cur.execute(
            "INSERT INTO model_binaries (model_id, version, binary_data) VALUES (%s, %s, %s) RETURNING id;",
            (model_id, version, binary_data),
        )
        binary_id = cur.fetchone()[0]
        app.logger.info(f"Binary uploaded with ID: {binary_id}")

        # Get JSON representation of the binary
        cur.execute(
            f"SELECT json_agg(json_build_object('id', model_binaries.id, 'model_id', model_binaries.model_id, 'version', model_binaries.version)) FROM model_binaries WHERE id = {binary_id};"
        )
        response = cur.fetchone()[0]

        db.commit()
        cur.close()

        app.logger.info(f"Binary response: {response}")

        # Return the response
        return Response(
            json.dumps(response[0], default=str),
            mimetype="application/json",
            status=201,
        )
    except Exception as e:
        app.logger.error(f"Error uploading binary: {e}")
        return Response(f"Error uploading binary: {e}", status=500)


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
