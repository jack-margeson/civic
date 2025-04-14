import os
import docker
import json
from colorama import Fore, Style, init
from enum import Enum
import signal
import prettytable

VERSION = "v0.1.0"

# Define menu options and states
menu_options = [
    [  # Global commands (0)
        {"key": "h", "command": "Help", "status": 1},
        {"key": "q", "command": "Exit", "status": 1},
        ### Hidden globals
        {"key": "help", "command": "h_help", "status": -1},
        {"key": "clear", "command": "h_clear", "status": -1},
        {"key": "exit", "command": "h_exit", "status": -1},
    ],
    [  # Main menu (1)
        {"key": "c", "command": "Manage Citizens", "status": 1},
    ],
    [  # Manage Citizens (2)
        {"key": "lc", "command": "List Citizens", "status": 1},
        {"key": "c", "command": "Create Citizen", "status": 1},
        {"key": "st", "command": "Start Citizen", "status": 1},
        {"key": "sp", "command": "Stop Citizen", "status": 1},
        {"key": "d", "command": "Delete Citizen", "status": 1},
        {"key": "b", "command": "Back", "status": 1},
    ],
]
menu_states = Enum("Menu", ["GLOBAL", "MAIN", "MANAGE_CITIZENS"], start=0)
menu_state_titles = ["Global Commands", "Main Menu", "Manage Citizens", "Manage Models"]
curr_menu = menu_states.MAIN

# Get the Docker client
docker_host = os.getenv("DOCKER_HOST_OVERRIDE", "unix://var/run/docker.sock")
client = docker.DockerClient(base_url=docker_host)

citizen_containers = []


# main()
# Main function to run the client
# It initializes the client, sets the current menu, and handles user input.
def main():
    os.system("clear")
    print_header()

    init_client()

    global curr_menu
    print_menu(curr_menu)

    while True:
        choice = input("$ ").lower().strip()

        ### Global commands (0)

        if choice in [item["key"] for item in menu_options[menu_states.GLOBAL.value]]:
            if any(
                choice == item["key"] and item["status"]
                for item in menu_options[menu_states.GLOBAL.value]
            ):
                match choice:
                    case "h":
                        print_menu(curr_menu)
                    case "q":
                        safe_exit()
                    # Hidden commands
                    case "help":
                        print_menu(curr_menu)
                    case "exit":
                        safe_exit()
                    case "clear":
                        os.system("clear")
            else:
                if any(
                    choice == item["key"]
                    for item in menu_options[menu_states.GLOBAL.value]
                ):
                    print_error("Command currently disabled. Please try again.")
                else:
                    print_error("Command not recognized. Please try again.")

        ### Main Menu (1)

        elif curr_menu == menu_states.MAIN:
            if any(
                choice == item["key"] and item["status"]
                for item in menu_options[menu_states.MAIN.value]
            ):
                match choice:
                    case "c":
                        set_curr_menu(menu_states.MANAGE_CITIZENS)
            else:
                if any(
                    choice == item["key"]
                    for item in menu_options[menu_states.MAIN.value]
                ):
                    print_error("Command currently disabled. Please try again.")
                else:
                    print_error("Command not recognized. Please try again.")

        ### Manage Citizens (2)

        elif curr_menu == menu_states.MANAGE_CITIZENS:
            if any(
                choice == item["key"] and item["status"]
                for item in menu_options[menu_states.MANAGE_CITIZENS.value]
            ):
                match choice:
                    case "lc":
                        list_citizens()
                    case "c":
                        create_citizen()
                    case "d":
                        delete_citizen()
                    case "st":
                        start_citizen()
                    case "sp":
                        stop_citizen()
                    case "b":
                        set_curr_menu(menu_states.MAIN)
            else:
                if any(
                    choice == item["key"]
                    for item in menu_options[menu_states.MANAGE_CITIZENS.value]
                ):
                    print_error("Command currently disabled. Please try again.")
                else:
                    print_error("Command not recognized. Please try again.")


# set_curr_menu()
# Helper function to set the current menu and print it
def set_curr_menu(menu_index):
    global curr_menu
    curr_menu = menu_index
    print_menu(curr_menu)


# print_header()
# Helper function to print the header
def print_header():
    header = "CIVIC Client {}".format(Fore.YELLOW + VERSION)
    print(Fore.GREEN + "=" * 30)
    print(Fore.GREEN + header.center(30 + len(Fore.YELLOW)))
    print(Fore.GREEN + "=" * 30)
    print(Style.RESET_ALL)


# print_menu()
# Helper function to print the menu
# It takes the menu index, header flag, and clear flag as arguments.
def print_menu(menu_index=menu_states.MAIN, header=False, clear=False):
    menu_index = menu_index.value

    # Clear screen
    os.system("clear") if clear else None

    print(Style.RESET_ALL)

    # Print header
    if header:
        print_header()

    # Print menu title
    print(
        Fore.LIGHTBLACK_EX
        + (" " + menu_state_titles[menu_index] + " ").center(25, "-")
        + Style.RESET_ALL
        + "\n"
    )

    # Get max key length for formatting
    max_key_length = max(len(item["key"]) for item in menu_options[menu_index])
    # Print specified menu
    for item in menu_options[menu_index]:
        color = Fore.BLUE if item["status"] else Fore.LIGHTBLACK_EX
        print(
            color + f"{(item['key'] + ')').ljust(max_key_length + 3)}{item['command']}"
        )
    print(Style.RESET_ALL)

    # Print GLOBAL menu title
    print(
        Fore.LIGHTBLACK_EX
        + (" " + menu_state_titles[menu_states.GLOBAL.value] + " ").center(25, "-")
        + Style.RESET_ALL
        + "\n"
    )

    # Print globals
    for item in menu_options[0]:
        if item["status"] != -1:
            color = Fore.BLUE if item["status"] else Fore.LIGHTBLACK_EX
            print(
                color
                + f"{(item['key'] + ')').ljust(max_key_length + 3)}{item['command']}"
            )
    print(Style.RESET_ALL)


# print_error()
# Helper function to print error messages
def print_error(message):
    print(Fore.RED + message + Style.RESET_ALL + "\n")


# print_table()
# Helper function to print a table
# It takes a list of dictionaries as input and formats it into a table using prettytable.
def print_table(data):
    headers = list(data[0].keys())
    data.insert(0, headers)
    table = prettytable.from_json(json.dumps(data))
    print(table, "\n")


# update_citizen_list()
# Updates the list of citizen containers
# It retrieves all containers from the Docker client and filters them based on their names.
# It updates the global citizen_containers variable with the filtered list.
def update_citizen_list():
    global client, citizen_containers
    citizen_containers = []
    for container in client.containers.list(all=True):
        if container.name.startswith("civic-internal-client"):
            citizen_containers.append(container)


# init_client()
# Initializes the client:
# It checks if the Docker image for the client exists, and if not, builds it.
# It also updates the list of citizen containers.
def init_client():
    global client

    print("Initializing client...")
    # Build the client container if it doesn't exist
    try:
        client.images.get("civic-internal-client")
    except docker.errors.ImageNotFound:
        print("Building citizen image...")
        client.images.build(
            path="./internal_client",
            dockerfile="Dockerfile",
            tag="civic-internal-client:latest",
        )

    update_citizen_list()

    print("Client initialized.")


# create_citizen()
# Creates a new citizen container
# It prompts the user for the server IP and port, and creates a new container with a unique ID.
# It also updates the list of citizen containers.
# It uses the Docker client to run the container with the specified environment variables.
def create_citizen():
    global client

    ip = (
        input("Enter the IP address of the server [default: localhost]: ")
        or "localhost"
    )
    port = input("Enter the port of the server [default: 24842]: ") or "24842"
    print(f"Creating citizen with server IP: {ip} and port: {port}")

    # Get the highest citizen id
    citizen_id = 1
    for container in citizen_containers:
        # Each citizen container has a unique id (starting from 1 and incrementing)
        # Check the highest id and increment by 1
        if int(container.name.split("-")[-1]) > len(citizen_containers):
            citizen_id = int(container.name.split("-")[-1]) + 1
        else:
            citizen_id = len(citizen_containers) + 1

    # Create citizen container
    client.containers.run(
        "civic-internal-client:latest",
        name=f"civic-internal-client-{citizen_id}",
        network="host",
        detach=True,
        environment={"CIVIC_SERVER_IP": ip, "CIVIC_SERVER_PORT": port},
    )
    update_citizen_list()


# list_citizens()
# Lists all citizen containers in a table format
def list_citizens():
    print("Listing citizens...")
    update_citizen_list()

    # List all running containers
    citizen_obj = []
    for container in citizen_containers:
        citizen_obj.append(
            {
                "id": container.name.split("-")[-1],
                "name": container.name,
                "status": container.status,
            }
        )
    if citizen_obj:
        citizen_obj.sort(key=lambda x: x["id"])
        print_table(citizen_obj)
    else:
        print("No citizens found.\n")


# delete_citizen()
# Deletes a citizen container
# It prompts the user for the ID of the citizen to delete and stops and removes the container.
def delete_citizen():
    list_citizens()
    citizen_id = input("Enter the ID of the citizen to delete: ").strip()

    # Find the container with the given ID
    container_to_delete = None
    for container in citizen_containers:
        if container.name.endswith(f"-{citizen_id}"):
            container_to_delete = container
            break

    if container_to_delete:
        confirmation = (
            input(f"Are you sure you want to delete citizen {citizen_id}? [y/N]: ")
            .strip()
            .lower()
        )
        if confirmation == "y":
            print(f"Stopping and removing citizen {citizen_id}...")
            container_to_delete.stop()
            container_to_delete.remove()
            citizen_containers.remove(container_to_delete)
            print(f"Citizen {citizen_id} deleted.")
            update_citizen_list()
        else:
            print("Deletion cancelled.")
    else:
        print_error("Citizen ID not found.")


# start_citizen()
# Starts a citizen container
# It prompts the user for the ID of the citizen to start and starts the container if it is stopped.
# It updates the list of citizen containers after starting.
# It uses the Docker client to start the container.
def start_citizen():
    list_citizens()
    citizen_id = input("Enter the ID of the citizen to start: ").strip()

    # Find the container with the given ID
    container_to_start = None
    for container in citizen_containers:
        if container.name.endswith(f"-{citizen_id}"):
            container_to_start = container
            break

    if container_to_start:
        if container_to_start.status == "exited":
            print(f"Starting citizen {citizen_id}...")
            container_to_start.start()
            print(f"Citizen {citizen_id} started.")
            update_citizen_list()
        else:
            print_error("Citizen is already running.")
    else:
        print_error("Citizen ID not found.")


# stop_citizen()
# Stops a citizen container
# It prompts the user for the ID of the citizen to stop and stops the container if it is running.
# It updates the list of citizen containers after stopping.
# It uses the Docker client to stop the container.
def stop_citizen():
    list_citizens()
    citizen_id = input("Enter the ID of the citizen to stop: ").strip()

    # Find the container with the given ID
    container_to_stop = None
    for container in citizen_containers:
        if container.name.endswith(f"-{citizen_id}"):
            container_to_stop = container
            break

    if container_to_stop:
        if container_to_stop.status == "running":
            print(f"Stopping citizen {citizen_id}...")
            container_to_stop.stop()
            print(f"Citizen {citizen_id} stopped.")
            update_citizen_list()
        else:
            print_error("Citizen is not running.")
    else:
        print_error("Citizen ID not found.")


# safe_exit()
# Safely exits the program.
def safe_exit():
    print("Exiting...")
    exit(0)


# signal_handler()
# Signal handler for SIGINT (Ctrl+C)
def signal_handler(sig, frame):
    safe_exit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
