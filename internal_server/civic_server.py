import socket
import threading
import logging


class CIVICServer:
    def __init__(self, host="127.0.0.1", port=65432):
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
                else:
                    break
            except ConnectionResetError:
                logging.info(f"Connection from {address} lost")
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = CIVICServer()
    server.start()
