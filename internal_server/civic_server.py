import socket
import threading
import logging
import signal
import time
import requests

logging.basicConfig(level=logging.INFO, force=True)

middleware_url = "http://civic-middleware:5000"


class CIVICServer:

    def __init__(self, host="0.0.0.0", port=24842):
        self.host = host
        self.port = port
        self.clients = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f"Server started on {self.host}:{self.port}")

    def handle_client(self, client_socket, address):
        # Handle a new client connection
        logging.info(f"New connection from {address}")

        # Handle the initial connection setup
        while True:
            try:
                # Receive the client's startup message
                client_startup_message = client_socket.recv(1024).decode("utf-8")

                if client_startup_message.startswith("UUID -1"):
                    # New client--add to database
                    client_uuid = self.db_update_client_connection(
                        address[0], address[1], 1
                    )
                    self.clients[client_uuid] = client_socket
                    # Send uuid to client
                    client_socket.send(("UUID " + str(client_uuid)).encode("utf-8"))
                    break
                elif client_startup_message.startswith("UUID "):
                    # Existing client--update database
                    client_uuid = client_startup_message.split(" ")[1]
                    client_uuid = self.db_update_client_connection(
                        address[0], address[1], 1, client_uuid
                    )
                    if client_uuid == -1:
                        raise Exception("UUID not found in database")
                    else:
                        self.clients[client_uuid] = client_socket
                        # Send uuid to client
                        client_socket.send(
                            # Existing client--update database
                            ("UUID " + str(client_uuid)).encode("utf-8")
                        )
                        break
            except Exception as e:
                logging.error(f"Error receiving UUID from client: {e}")
                client_socket.send("Invalid UUID".encode("utf-8"))
                client_socket.close()
                return

        while True:
            try:
                message = client_socket.recv(1024).decode("utf-8")
                if message:
                    logging.info(f"Received message from {address}: {message}")
                    # Handle commands from the client here
                    if message.lower() == "exit":
                        logging.info(f"Connection from {address} closed")
                        self.db_update_client_connection(
                            address[0], address[1], 0, client_uuid=client_uuid
                        )
                        if client_uuid in self.clients:
                            del self.clients[client_uuid]
                        client_socket.close()
                        break
                    elif message.lower() == "ping":
                        client_socket.send("pong".encode("utf-8"))
                    else:
                        client_socket.send("Message not recognized".encode("utf-8"))
                else:
                    break
            except ConnectionResetError:
                logging.info(f"Connection from {address} lost")
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
                break
            except Exception as e:
                logging.error(f"An error occurred with connection from {address}: {e}")
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
                break

    def start(self):
        logging.info("Server is running and waiting for connections...")
        while True:
            client_socket, address = self.server_socket.accept()
            client_thread = threading.Thread(
                target=self.handle_client, args=(client_socket, address)
            )
            client_thread.start()

    def safe_exit(self, sig, frame):
        logging.info("Exiting server...")
        for client_socket in self.clients.values():
            try:
                client_socket.send("Server is shutting down".encode("utf-8"))
            except Exception as e:
                logging.error(f"Error notifying client: {e}")

        # Wait for clients to disconnect or timeout after 30 seconds
        timeout = 30
        start_time = time.time()
        while self.clients and (time.time() - start_time) < timeout:
            for client_socket in self.clients.values():
                try:
                    client_socket.close()
                except Exception as e:
                    logging.error(f"Error closing client connection: {e}")
            time.sleep(1)
        self.server_socket.close()
        logging.info("Server closed.")
        exit(0)

    def db_update_client_connection(
        self,
        ip,
        port,
        status,
        client_uuid=-1,
    ):
        # Update the database with the client's connection information
        if status == 1 and client_uuid == -1:
            # New client
            client_data = {"ip": ip, "port": port, "status": 1}  # active
            try:
                response = requests.post(f"{middleware_url}/clients", json=client_data)
                response.raise_for_status()
                client_uuid = response.json()[0].get("client_uuid")
                return client_uuid
            except requests.RequestException as e:
                logging.error(
                    f"Failed to update client connection in the database: {e}"
                )
                raise
        if status == 1 and client_uuid != -1:
            # Existing client
            client_data = {"ip": ip, "port": port, "status": 1}
            try:
                response = requests.put(
                    f"{middleware_url}/clients/{client_uuid}/activate", json=client_data
                )
                response.raise_for_status()
                return client_uuid
            except requests.RequestException as e:
                logging.error(
                    f"Failed to update client connection in the database: {e}"
                )
                raise
        else:
            # Disconnecting client
            try:
                response = requests.put(
                    f"{middleware_url}/clients/{client_uuid}/deactivate"
                )
                response.raise_for_status()
            except requests.RequestException as e:
                logging.error(
                    f"Failed to update client disconnection in the database: {e}"
                )
                raise


if __name__ == "__main__":
    server = CIVICServer()
    signal.signal(signal.SIGINT, server.safe_exit)
    signal.signal(signal.SIGTERM, server.safe_exit)
    server.start()
