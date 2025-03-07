import sys
import socket
import logging
import threading
import os
import signal

logging.basicConfig(level=logging.INFO)

CIVIC_SERVER_IP = ""
CIVIC_SERVER_PORT = ""

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


def connect_to_server():
    global s, listener_thread

    logging.info(f"Connecting to server at {CIVIC_SERVER_IP}:{CIVIC_SERVER_PORT}...")

    # Create a socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.connect((CIVIC_SERVER_IP, int(CIVIC_SERVER_PORT)))
        logging.info("Successfully connected to the server.")

        # Send a ping message
        s.sendall(b"ping")
        logging.info("Ping message sent to the server.")

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
                decoded_response = response.decode()
                logging.info(f"Received response from server: {decoded_response}")
                if decoded_response == "Server is shutting down":
                    safe_exit()
            else:
                safe_exit()
        except socket.error as e:
            logging.error(f"Socket error: {e}")
            break


def safe_exit(*args):
    global s
    logging.info("Closing connection...")
    if s:
        try:
            s.sendall("exit".encode("utf-8"))
            s.close()
        except socket.error as e:
            logging.error(f"Socket error: {e}")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, safe_exit)
    signal.signal(signal.SIGTERM, safe_exit)

    main()
