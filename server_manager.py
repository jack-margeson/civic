# creates server instance (flask middleware, postgresql database, etc)
# handles model creation, editing, deletion
# talks to the middleware server to pass along model data
# talks directly to internal_clients to issue work orders and receive data
# stores data in postgresql database through the middleware server

import os
import json
import requests
import docker
from colorama import Fore, Style, init
from enum import Enum
import signal
import prettytable

VERSION = "v0.1.0"

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
        {"key": "i", "command": "Install CIVIC Server", "status": 1},
        {"key": "u", "command": "Uninstall CIVIC Server", "status": 1},
        {"key": "l", "command": "List Models", "status": 1},
        {"key": "m", "command": "Manage Models", "status": 1},
    ],
]
menu_states = Enum("Menu", ["GLOBAL", "MAIN"], start=0)
menu_state_titles = ["Global Commands", "Main Menu"]
curr_menu = menu_states.MAIN

# Get the Docker client
docker_host = os.getenv("DOCKER_HOST_OVERRIDE", "unix://var/run/docker.sock")
client = docker.DockerClient(base_url=docker_host)

middleware_url = "http://localhost:5000"


def main():
    os.system("clear")
    print_header()

    init_server_manager()

    global curr_menu
    print_menu(curr_menu)

    while True:
        choice = input("$ ").lower()

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
                    case "i":
                        install_civic_server()
                    case "u":
                        uninstall_civic_server()
                    case "l":
                        list_models()
                    case "m":
                        manage_models()
            else:
                if any(
                    choice == item["key"]
                    for item in menu_options[menu_states.MAIN.value]
                ):
                    print_error("Command currently disabled. Please try again.")
                else:
                    print_error("Command not recognized. Please try again.")


def set_curr_menu(menu_index):
    global curr_menu
    curr_menu = menu_index
    print_menu(curr_menu)


def print_header():
    header = "CIVIC Server Manager {}".format(Fore.YELLOW + VERSION)
    print(Fore.GREEN + "=" * 30)
    print(Fore.GREEN + header.center(30 + len(Fore.YELLOW)))
    print(Fore.GREEN + "=" * 30)
    print(Style.RESET_ALL)


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


def print_error(message):
    print(Fore.RED + message + Style.RESET_ALL + "\n")


def print_table(data):
    headers = list(data[0].keys())
    data.insert(0, headers)
    table = prettytable.from_json(json.dumps(data))
    print(table, "\n")


def init_server_manager():
    global client  # Docker client
    print("Initializing server manager...")

    # Check if the CIVIC server is running
    running = all(
        container.name in ["civic-middleware", "civic-db", "civic-adminer"]
        for container in client.containers.list()
    )
    if running:
        # Disable "Install CIVIC Server" option
        menu_options[1][0]["status"] = 0
    else:
        # Disable "Uninstall CIVIC Server" option
        menu_options[1][1]["status"] = 0


def install_civic_server():
    global client

    uninstall_civic_server(quiet=True)

    print(Fore.GREEN + "Installing CIVIC Server..." + Style.RESET_ALL)

    # Build the images
    print("Building images...")
    client.images.build(
        path="./middleware", dockerfile="Dockerfile", tag="civic-middleware:latest"
    )
    client.images.build(path="./sql", dockerfile="Dockerfile", tag="civic-db:latest")
    client.images.pull("adminer", tag="latest")
    client.images.build(
        path="./internal_server",
        dockerfile="Dockerfile",
        tag="civic-internal-server:latest",
    )

    # Create the network
    print("Creating network...")
    client.networks.create(
        "civic-network",
        driver="bridge",
        ipam=docker.types.IPAMConfig(
            pool_configs=[
                docker.types.IPAMPool(subnet="172.20.0.0/16", gateway="172.20.0.1")
            ]
        ),
    )

    # Create the volume
    print("Creating volumes...")
    client.volumes.create(name="civic-db")

    # Create and start the containers
    print("Creating and starting containers...")

    client.containers.run(
        "civic-db:latest",
        name="civic-db",
        ports={"5432/tcp": 5432},
        restart_policy={"Name": "always"},
        environment={
            "POSTGRES_USER": "civic_db_admin",
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        },
        volumes=["civic-db:/var/lib/postgresql/data"],
        mounts=[
            docker.types.Mount(
                source=os.path.abspath("./sql/init.sql"),
                target="/docker-entrypoint-initdb.d/init.sql",
                type="bind",
                read_only=True,
            )
        ],
        healthcheck={
            "test": ["CMD-SHELL", "pg_isready -U $POSTGRES_USER"],
            "interval": 5000000000,
            "timeout": 5000000000,
            "retries": 5,
        },
        network="civic-network",
        detach=True,
    )

    client.containers.run(
        "civic-middleware:latest",
        name="civic-middleware",
        ports={"5000/tcp": 5000},
        restart_policy={"Name": "always"},
        environment={
            "POSTGRES_USER": "civic_db_admin",
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        },
        network="civic-network",
        detach=True,
    )

    client.containers.run(
        "adminer:latest",
        name="civic-adminer",
        ports={"8080/tcp": 8080},
        restart_policy={"Name": "always"},
        network="civic-network",
        detach=True,
    )

    client.containers.run(
        "civic-internal-server:latest",
        name="civic-internal-server",
        ports={"24842/tcp": 24842},
        restart_policy={"Name": "always"},
        network="civic-network",
        detach=True,
    )

    print(Fore.GREEN + "CIVIC Server installed!\n" + Style.RESET_ALL)

    # Disable "Install CIVIC Server" option
    menu_options[1][0]["status"] = 0
    # Enable "Uninstall CIVIC Server" option
    menu_options[1][1]["status"] = 1


def uninstall_civic_server(quiet=False):
    global client

    if not quiet:
        print(Fore.RED + "Uninstalling CIVIC Server..." + Style.RESET_ALL)
    # Stop and remove the containers
    if not quiet:
        print("Stopping and removing containers...")
    for container in client.containers.list():
        if container.name in [
            "civic-server",
            "civic-middleware",
            "civic-db",
            "civic-adminer",
            "civic-internal-server",
        ]:
            container.stop()
            container.remove(force=True)
    # Remove the network
    if not quiet:
        print("Removing network...")
    for network in client.networks.list():
        if network.name == "civic-network":
            network.remove()
    # Remove the volume
    if not quiet:
        print("Removing volumes...")
    for volume in client.volumes.list():
        if volume.name == "civic-db":
            volume.remove()
    # Delete the images
    if not quiet:
        print("Deleting images...")
    for image in client.images.list():
        if image.tags == [
            "civic-middleware:latest",
            "civic-db:latest",
            "civic-internal-server:latest",
        ]:
            client.images.remove(image.id)

    if not quiet:
        print(Fore.RED + "CIVIC Server uninstalled.\n" + Style.RESET_ALL)

    # Enable "Install CIVIC Server" option
    menu_options[1][0]["status"] = 1
    # Disable "Uninstall CIVIC Server" option
    menu_options[1][1]["status"] = 0


def list_models():
    print("Modules:")
    response = requests.get(f"{middleware_url}/get_models")
    response.raise_for_status()
    print_table(response.json())


def manage_models():
    print("Managing models...")  # TODO


def safe_exit():
    print("Exiting...")
    exit(0)


def signal_handler(sig, frame):
    safe_exit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
