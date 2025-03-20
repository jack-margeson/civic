import socket
import threading
import logging
import signal
import curses
import requests
import time
import os
import json
import prettytable

middleware_url = "http://civic-middleware:5000"


class CursesLoggerHandler(logging.Handler):
    def __init__(self, stdscr):
        super().__init__()
        self.stdscr = stdscr
        self.log_pad = curses.newpad(
            1000, curses.COLS
        )  # Create a pad with a large height
        self.log_pad_pos = 0  # Track the current scroll position

    def emit(self, record):
        try:
            msg = self.format(record)
            try:
                self.log_pad.addstr(self.log_pad_pos, 0, msg + "\n")
                self.log_pad_pos += 1
                # Ensure the pad scrolls up when the bottom is reached
                max_y, max_x = self.stdscr.getmaxyx()
                self.log_pad.refresh(
                    max(0, self.log_pad_pos - max_y + 1), 0, 0, 0, max_y - 1, max_x - 1
                )
            except curses.error:
                pass  # Ignore curses errors caused by terminal size or cursor issues
        except Exception:
            self.handleError(record)


class CIVICServer:
    def __init__(self, stdscr, host="0.0.0.0", port=24842):
        self.stdscr = stdscr
        self.server_running = False
        self.host = host
        self.port = port
        self.clients = {}
        self.logger_handler = None
        self.server_socket = None
        self.server_command_thread = None

        # Init. the server
        self.init_server()

    def init_server(self):
        # Create a "download" folder if it doesn't exist
        if not os.path.exists("download"):
            os.makedirs("download")

        # Set up logging
        self.logger_handler = CursesLoggerHandler(self.stdscr)
        logging.getLogger().addHandler(self.logger_handler)
        logging.getLogger().setLevel(logging.INFO)

        # Start the server
        self.server_running = True
        # Make and open the server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f"Server started on {self.host}:{self.port}")

    # TODO: curses stdscr REALLY doesn't work well with Docker. It's a pain to get it to work.
    # The problem is that the terminal size is detected for the container, but when attaching
    # to the container, the terminal size is different. This causes the curses pad to be the wrong size.
    # I've tried a few different solutions, but none have worked well. I'm going to leave this as is for now.
    def handle_server_commands(self):
        try:
            curses.curs_set(1)
            max_y, max_x = self.stdscr.getmaxyx()
            input_win = curses.newwin(1, max_x, max_y - 1, 0)
            input_win.timeout(100)  # Set a timeout of 100ms for non-blocking input
        except curses.error as e:
            logging.error(f"Curses initialization error: {e}")
            return

        command_buffer = ""
        while self.server_running:
            input_win.erase()
            input_win.addstr(0, 0, f"$ {command_buffer}")
            input_win.refresh()
            try:
                key = input_win.getch()
                if key == -1:  # No input
                    continue
                elif key in (curses.KEY_BACKSPACE, 127):  # Handle backspace
                    command_buffer = command_buffer[:-1]
                elif key in (10, 13):  # Handle Enter key
                    command = command_buffer.strip()
                    command_buffer = ""
                    if not command:
                        continue

                    args = command.split()
                    cmd = args[0].lower()
                    cmd_args = args[1:]

                    if cmd in ["help", "h"]:
                        logging.info("Available commands:")
                        logging.info("  clients - List all connected clients.")
                        logging.info("  models - List all available models.")
                        logging.info(
                            "  download <model_id> - Download a model's binary by its ID."
                        )
                        logging.info("  shutdown - Shut down the server.")
                    elif cmd in ["exit", "quit", "q"]:
                        logging.info("To detach from the server console, use Ctrl+D.")
                    elif cmd in ["clients", "citizens", "lc"]:
                        self.list_clients()
                    elif cmd in ["models", "lm"]:
                        self.list_models()
                    elif cmd == "download":
                        if not cmd_args:
                            logging.info("Usage: download <model_id>")
                            continue
                        model_id = cmd_args[0]
                        self.download_binary(model_id)
                    elif cmd == "distribute":
                        if len(cmd_args) < 3:
                            logging.info(
                                "Usage: distribute <model_id> <range_start> <range_end>"
                            )
                            continue
                        model_id = cmd_args[0]
                        range_start = int(cmd_args[1])
                        range_end = int(cmd_args[2])
                        self.distribute_binary(model_id, range_start, range_end)
                    elif cmd == "shutdown":
                        os.kill(os.getpid(), signal.SIGINT)
                    else:
                        logging.info(f"Command not recognized: {command}")
                else:
                    command_buffer += chr(key)
            except Exception as e:
                logging.error(f"Error handling input: {e}")

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

    def start(self):
        logging.info("Server is running and waiting for connections...")
        self.server_command_thread = threading.Thread(
            target=self.handle_server_commands, daemon=True
        )
        self.server_command_thread.start()
        while True:
            client_socket, address = self.server_socket.accept()
            client_thread = threading.Thread(
                target=self.handle_client, args=(client_socket, address)
            )
            client_thread.start()

    def safe_exit(self, *_):
        logging.info("Exiting server...")
        self.server_running = False

        # Notify all clients that the server is shutting down
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

        # Close the server socket
        self.server_socket.close()

        curses.endwin()
        exit(0)

    def print_table(self, data):
        headers = list(data[0].keys())
        data.insert(0, headers)
        table = prettytable.from_json(json.dumps(data))
        for line in str(table).splitlines():
            logging.info(line)

    ### SERVER COMMANDS ###

    def list_clients(self, all_clients=True):
        # TODO: Implement all_clients functionality--another endpoint?
        logging.info("Listing clients...")
        response = requests.get(f"{middleware_url}/clients")
        response.raise_for_status()
        if response.json():
            self.print_table(response.json())
        else:
            logging.info("No clients found.")

    def list_models(self, all_models=True):
        logging.info("Listing models...")
        response = requests.get(f"{middleware_url}/get_models")
        response.raise_for_status()
        if response.json():
            self.print_table(response.json())
        else:
            logging.info("No models found.")

    def download_binary(self, model_id):
        try:
            response = requests.get(
                f"{middleware_url}/download_binary/{model_id}", stream=True
            )
            response.raise_for_status()

            # Save the model binary to a file
            file_path = os.path.join("download", f"model_{model_id}.bin")
            with open(file_path, "wb") as model_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        model_file.write(chunk)

            logging.info(f"Model {model_id} downloaded successfully to {file_path}")
        except requests.RequestException as e:
            logging.error(f"Failed to download model {model_id}: {e}")

    def distribute_binary(self, model_id, range_start, range_end):
        # Given a model ID and a range of clients, distribute the model binary to those clients
        try:
            # Check if the model binary exists
            file_path = os.path.join("download", f"model_{model_id}.bin")
            if not os.path.exists(file_path):
                logging.warning(
                    f"Model binary for {model_id} not found. Please download it first."
                )
                return

            if self.clients:
                # Validate range
                if range_start < 0 or range_end >= len(self.clients):
                    logging.warning(
                        "Invalid range. Please provide a valid range of clients."
                    )
                    return

                # Get the list of clients within the specified range
                client_list = list(self.clients.items())[range_start : range_end + 1]

                # Read the model binary
                with open(file_path, "rb") as model_file:
                    model_data = model_file.read()

                # Distribute the model binary to the selected clients
                for client_uuid, client_socket in client_list:
                    try:
                        # Send the model ID and binary size first
                        binary_size = len(model_data)
                        client_socket.sendall(
                            f"MODEL_BIN {model_id} {binary_size}".encode("utf-8")
                        )

                        # Send the binary data in chunks
                        chunk_size = 8192
                        for i in range(0, binary_size, chunk_size):
                            client_socket.sendall(model_data[i : i + chunk_size])

                        logging.info(
                            f"Model {model_id} binary distributed to client {client_uuid}"
                        )
                    except Exception as e:
                        logging.error(
                            f"Failed to send model {model_id} to client {client_uuid}: {e}"
                        )
            else:
                logging.warning("No clients connected to distribute the model to.")
                return

        except requests.RequestException as e:
            logging.error(f"Failed to distribute model {model_id}: {e}")


def main(stdscr):
    server = CIVICServer(stdscr)
    signal.signal(signal.SIGINT, server.safe_exit)
    signal.signal(signal.SIGTERM, server.safe_exit)
    server.start()


if __name__ == "__main__":
    curses.wrapper(main)
