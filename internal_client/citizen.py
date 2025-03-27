import sys
import socket
import logging
import threading
import os
import signal
import json
import subprocess

logging.basicConfig(level=logging.DEBUG)

CIVIC_SERVER_IP = ""
CIVIC_SERVER_PORT = ""

CLIENT_UUID = None

s = None
listener_thread = None


def main():
    configure()
    connect_to_server()
    if listener_thread:
        listener_thread.join()  # Wait for the listener thread to complete


def configure():
    global CIVIC_SERVER_IP, CIVIC_SERVER_PORT
    CIVIC_SERVER_IP = os.getenv("CIVIC_SERVER_IP")
    CIVIC_SERVER_PORT = os.getenv("CIVIC_SERVER_PORT")
    if not os.getenv("CIVIC_SERVER_IP") or not os.getenv("CIVIC_SERVER_PORT"):
        logging.fatal("CIVIC_SERVER_IP and CIVIC_SERVER_PORT must be set.")
        sys.exit(1)

    # Load the client's UUID from a file if it exists
    if os.path.exists("citizen_uuid"):
        with open("citizen_uuid", "r") as uuid_file:
            global CLIENT_UUID
            CLIENT_UUID = uuid_file.read().strip()
            logging.info(f"Loaded client UUID: {CLIENT_UUID}")

    # Create a download and temp directory if it doesn't exist
    os.makedirs("download", exist_ok=True)
    os.makedirs("temp", exist_ok=True)


def connect_to_server():
    global s, listener_thread

    logging.info(f"Connecting to server at {CIVIC_SERVER_IP}:{CIVIC_SERVER_PORT}...")

    # Create a socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.connect((CIVIC_SERVER_IP, int(CIVIC_SERVER_PORT)))
        logging.info("Successfully connected to the server.")

        if CLIENT_UUID:
            logging.info(f"Sending pre-established UUID to server: {CLIENT_UUID}")
            s.sendall(f"UUID {CLIENT_UUID}".encode("utf-8"))
        else:
            logging.info("Requesting a new UUID from the server...")
            s.sendall("UUID -1".encode("utf-8"))

        # Start a thread to listen for messages from the server
        listener_thread = threading.Thread(target=listen_for_messages, daemon=True)
        listener_thread.start()

    except socket.error as e:
        logging.error(f"Socket error: {e}")


def listen_for_messages():
    global s
    while True:
        try:
            response = s.recv(1024)

            if response:
                message = response.decode()
                logging.info(f"Received response from server: {message}")
                if message.startswith("UUID "):
                    client_uuid = message.split(" ")[1]
                    logging.info(f"Client UUID: {client_uuid}")
                    with open("citizen_uuid", "w") as uuid_file:
                        uuid_file.write(client_uuid)
                if message.startswith("MODEL_BIN"):
                    download_binary(message)
                if message.startswith("EXECUTE"):
                    execute_binary(message)
                if message.startswith("DUTY"):
                    execute_duty(message)
                if message == "Server is shutting down":
                    safe_exit()

            else:
                safe_exit()
        except socket.error as e:
            logging.error(f"Socket error: {e}")
            break


def download_binary(message):
    global s

    logging.info("Downloading model binary from the server...")
    model_id, binary_size = message.split(" ")[1:3]
    binary_size = int(binary_size)
    model_data = b""

    received_size = 0
    while received_size < binary_size:
        chunk = s.recv(8192)
        if not chunk:
            logging.error("Connection lost while downloading binary.")
            return
        model_data += chunk
        received_size += len(chunk)
        logging.debug(f"Received {received_size}/{binary_size} bytes")

    # Save the received model binary to a file
    file_path = os.path.join("download", f"model_{model_id}.bin")
    with open(file_path, "wb") as model_file:
        model_file.write(model_data)

    # Make the file executable
    os.chmod(file_path, 0o755)

    logging.info(
        f"Model {model_id} binary received from the server and saved to {file_path}"
    )


def execute_binary(message):
    global s

    logging.info("Executing model binary...")
    model_id = message.split(" ")[1]
    file_path = os.path.join("download", f"model_{model_id}.bin")

    # Execute the model binary
    try:
        subprocess.run([file_path], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing model binary: {e}")
        return

    logging.info(f"Model {model_id} binary executed.")


def execute_duty(message):
    global s

    logging.info("Executing duty...")
    duty_raw = message.split(" ", 1)[1]
    duty = json.loads(duty_raw)

    #   Example duty
    #   {
    #     "id": 1,
    #     "model_id": 2,
    #     "split_id": 0,
    #     "data": [
    #       {
    #         "letter": "a"
    #       }
    #     ],
    #     "created_at": "2025-03-24 20:40:39.299980"
    #   }

    # Check if the model binary for the duty exists
    model_id = duty["model_id"]
    file_path = os.path.join("download", f"model_{model_id}.bin")
    if not os.path.exists(file_path):
        logging.error(f"Model {model_id} binary does not exist.")
        return

    # Save the "data" field to a input file in the temp directory
    input_file_path = os.path.join("temp", f"duty_{duty['id']}")
    with open(input_file_path, "w") as input_file:
        json.dump(duty["data"], input_file)

    # Execute the model binary with the input file
    output_file_path = os.path.join("temp", f"duty_{duty['id']}_output")
    try:
        subprocess.run([file_path, input_file_path, output_file_path], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing model binary: {e}")
        return

    logging.info(f"Duty {duty['id']} executed.")

    # Read the output file and send the result back to the server
    with open(output_file_path, "r") as output_file:
        output_data = output_file.read()
        logging.info(f"Output data: {output_data}")

    s.sendall(f"RESULTS {duty['id']} {duty['model_id']} {output_data}".encode("utf-8"))
    s.sendall(f"READY".encode("utf-8"))


def safe_exit(*args):
    global s
    logging.info("Closing connection...")
    if s:
        try:
            s.sendall("EXIT".encode("utf-8"))
            s.close()
        except socket.error as e:
            logging.error(f"Socket error: {e}")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, safe_exit)
    signal.signal(signal.SIGTERM, safe_exit)

    main()
