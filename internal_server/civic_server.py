import socket
import threading
import logging
import signal
import time

logging.basicConfig(level=logging.INFO, force=True)

middleware_url = "http://localhost:5000"


class CIVICServer:

    def __init__(self, host="0.0.0.0", port=24842):
        self.host = host
        self.port = port
        self.clients = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f"Server started on {self.host}:{self.port}")

    def handle_client(self, client_socket, address):
        logging.info(f"New connection from {address}")
        self.clients.append(client_socket)
        while True:
            try:
                message = client_socket.recv(1024).decode("utf-8")
                if message:
                    logging.info(f"Received message from {address}: {message}")
                    # Handle commands from the client here
                    if message.lower() == "exit":
                        logging.info(f"Connection from {address} closed")
                        self.clients.remove(client_socket)
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
        for client in self.clients:
            try:
                client.send("Server is shutting down".encode("utf-8"))
            except Exception as e:
                logging.error(f"Error notifying client: {e}")

        # Wait for clients to disconnect or timeout after 30 seconds
        timeout = 30
        start_time = time.time()
        while self.clients and (time.time() - start_time) < timeout:
            for client in self.clients:
                try:
                    client.close()
                except Exception as e:
                    logging.error(f"Error closing client connection: {e}")
            time.sleep(1)
        self.server_socket.close()
        logging.info("Server closed.")
        exit(0)


if __name__ == "__main__":
    server = CIVICServer()
    signal.signal(signal.SIGINT, server.safe_exit)
    signal.signal(signal.SIGTERM, server.safe_exit)
    server.start()
