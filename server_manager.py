import base64
import os
import json
import requests
import docker
from colorama import Fore, Style, init
from enum import Enum
import signal
import prettytable
import csv

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
        {"key": "i", "command": "Install CIVIC Server", "status": 1},
        {"key": "u", "command": "Uninstall CIVIC Server", "status": 1},
        {"key": "ms", "command": "Manage CIVIC Server", "status": 1},
        {"key": "mm", "command": "Manage Models", "status": 1},
        {"key": "md", "command": "Manage Datasets", "status": 1},
    ],
    [  # Manage server (2)
        {"key": "a", "command": "Attach to Server Console", "status": 1},
        {"key": "st", "command": "Start Server", "status": 1},
        {"key": "sp", "command": "Stop Server", "status": 1},
        {"key": "b", "command": "Back", "status": 1},
    ],
    [  # Manage models (3)
        {"key": "lm", "command": "List Models", "status": 1},
        {"key": "c", "command": "Create Model", "status": 1},
        {"key": "e", "command": "Edit Model", "status": 1},
        {"key": "s", "command": "Change Model Status", "status": 1},
        {"key": "lb", "command": "List Model Binaries", "status": 1},
        {"key": "u", "command": "Upload New Model Binary", "status": 1},
        {"key": "b", "command": "Back", "status": 1},
    ],
    [  # Manage datasets (4)
        {"key": "c", "command": "Create Dataset", "status": 1},
        {"key": "d", "command": "Delete Dataset", "status": 1},
        {"key": "b", "command": "Back", "status": 1},
    ],
]
menu_states = Enum(
    "Menu",
    ["GLOBAL", "MAIN", "MANAGE_SERVER", "MANAGE_MODELS", "MANAGE_DATASETS"],
    start=0,
)
menu_state_titles = [
    "Global Commands",
    "Main Menu",
    "Manage CIVIC Server",
    "Manage Models",
    "Manage Datasets",
]
curr_menu = menu_states.MAIN

# Get the Docker client
docker_host = os.getenv("DOCKER_HOST_OVERRIDE", "unix://var/run/docker.sock")
client = docker.DockerClient(base_url=docker_host)

middleware_url = "http://localhost:5000"


# main()
# Handles the main loop of the server manager.
# It initializes the server manager, prints the menu, and handles user input.
def main():
    os.system("clear")
    print_header()

    init_server_manager()

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
                    case "i":
                        install_civic_server()
                    case "u":
                        uninstall_civic_server()
                    case "ms":
                        set_curr_menu(menu_states.MANAGE_SERVER)
                    case "mm":
                        set_curr_menu(menu_states.MANAGE_MODELS)
                    case "md":
                        set_curr_menu(menu_states.MANAGE_DATASETS)
            else:
                if any(
                    choice == item["key"]
                    for item in menu_options[menu_states.MAIN.value]
                ):
                    print_error("Command currently disabled. Please try again.")
                else:
                    print_error("Command not recognized. Please try again.")

        ### Manage Server (2)
        elif curr_menu == menu_states.MANAGE_SERVER:
            if any(
                choice == item["key"] and item["status"]
                for item in menu_options[menu_states.MANAGE_SERVER.value]
            ):
                match choice:
                    case "a":
                        attach_to_server()
                    case "st":
                        start_server()
                    case "sp":
                        stop_server()
                    case "b":
                        set_curr_menu(menu_states.MAIN)
            else:
                if any(
                    choice == item["key"]
                    for item in menu_options[menu_states.MANAGE_SERVER.value]
                ):
                    print_error("Command currently disabled. Please try again.")
                else:
                    print_error("Command not recognized. Please try again.")

        ### Manage Models (3)
        elif curr_menu == menu_states.MANAGE_MODELS:
            if any(
                choice == item["key"] and item["status"]
                for item in menu_options[menu_states.MANAGE_MODELS.value]
            ):
                match choice:
                    case "lm":
                        list_models()
                    case "c":
                        create_model()
                    case "e":
                        edit_model()
                    case "s":
                        change_model_status()
                    case "lb":
                        list_model_binaries()
                    case "u":
                        upload_model_binary()
                    case "b":
                        set_curr_menu(menu_states.MAIN)
            else:
                if any(
                    choice == item["key"]
                    for item in menu_options[menu_states.MANAGE_MODELS.value]
                ):
                    print_error("Command currently disabled. Please try again.")
                else:
                    print_error("Command not recognized. Please try again.")

            ### Manage Datasets (4)
        elif curr_menu == menu_states.MANAGE_DATASETS:
            if any(
                choice == item["key"] and item["status"]
                for item in menu_options[menu_states.MANAGE_DATASETS.value]
            ):
                match choice:
                    case "c":
                        create_dataset()
                    case "d":
                        print("Delete Dataset")  # TODO
                    case "b":
                        set_curr_menu(menu_states.MAIN)
            else:
                if any(
                    choice == item["key"]
                    for item in menu_options[menu_states.MANAGE_DATASETS.value]
                ):
                    print_error("Command currently disabled. Please try again.")
                else:
                    print_error("Command not recognized. Please try again.")

        update_menu_state()


# set_curr_menu()
# Helper function to set the current menu and print it
def set_curr_menu(menu_index):
    global curr_menu
    curr_menu = menu_index
    print_menu(curr_menu)


# print_header()
# Helper function to print the header
def print_header():
    header = "CIVIC Server Manager {}".format(Fore.YELLOW + VERSION)
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


# print_success()
# Helper function to print success messages
def print_success(message):
    print(Fore.GREEN + message + Style.RESET_ALL + "\n")


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


# update_menu_state()
# Helper function to update the menu state
# It checks the status of the CIVIC server and updates the menu options accordingly.
def update_menu_state():
    global client

    # Check if the middleware container is present
    # If so, the server is installed
    if any(
        container.name == "civic-middleware"
        for container in client.containers.list(all=True)
    ):
        # Disable "Install CIVIC Server" option
        menu_options[1][0]["status"] = 0
        # Enable "Uninstall CIVIC Server" option
        menu_options[1][1]["status"] = 1
        # Enable "Manage Server" option
        menu_options[1][2]["status"] = 1
        # Enable "Manage Models" option
        menu_options[1][3]["status"] = 1
        # Enable "Manage Datasets" option
        menu_options[1][4]["status"] = 1
    else:
        # Enable "Install CIVIC Server" option
        menu_options[1][0]["status"] = 1
        # Disable "Uninstall CIVIC Server" option
        menu_options[1][1]["status"] = 0
        # Disable "Manage Server" option
        menu_options[1][2]["status"] = 0
        # Disable "Manage Models" option
        menu_options[1][3]["status"] = 0
        # Disable "Manage Datasets" option
        menu_options[1][4]["status"] = 0

    # Check if the internal server is running
    if any(
        container.name == "civic-internal-server" and container.status == "running"
        for container in client.containers.list(all=True)
    ):
        # Enable "Attach to Server Console" option
        menu_options[2][0]["status"] = 1
        # Disable "Start Server" option
        menu_options[2][1]["status"] = 0
        # Enable "Stop Server" option
        menu_options[2][2]["status"] = 1
    else:
        # Disable "Attach to Server Console" option
        menu_options[2][0]["status"] = 0
        # Enable "Start Server" option
        menu_options[2][1]["status"] = 1
        # Disable "Stop Server" option
        menu_options[2][2]["status"] = 0


# init_server_manager()
# Initializes the server manager (currently, just updates the menu state).
def init_server_manager():
    print("Initializing server manager...")
    update_menu_state()


# install_civic_server()
# Installs the CIVIC server by building the images, creating the network and volume, and starting the containers.
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
        network="civic-network",
        tty=True,
        stdin_open=True,
        detach=True,
    )

    print_success("CIVIC Server installed!")


# uninstall_civic_server()
# Uninstalls the CIVIC server by stopping and removing the containers, network, and volume.
def uninstall_civic_server(quiet=False):
    global client

    if not quiet:
        print(Fore.RED + "Uninstalling CIVIC Server..." + Style.RESET_ALL)
    # Stop and remove the containers
    if not quiet:
        print("Stopping and removing containers...")
    for container in client.containers.list(all=True):
        if container.name in [
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
    for image in client.images.list(all=True):
        if image.tags == [
            "civic-middleware:latest",
            "civic-db:latest",
            "civic-internal-server:latest",
            # Don't delete adminer, pain to redownload
        ]:
            client.images.remove(image.id)

    if not quiet:
        print(Fore.RED + "CIVIC Server uninstalled.\n" + Style.RESET_ALL)


# start_server()
# Starts the CIVIC server by starting the containers.
def start_server():
    global client
    print("Starting the CIVIC server...")
    for container in client.containers.list(all=True):
        if container.name in [
            "civic-middleware",
            "civic-db",
            "civic-adminer",
            "civic-internal-server",
        ]:
            if container.status != "running":
                container.start()
    print_success("CIVIC Server started.")


# stop_server()
# Stops the CIVIC server by stopping the containers.
def stop_server():
    global client
    print("Stopping the CIVIC server...")
    for container in client.containers.list(all=True):
        if container.name in [
            "civic-middleware",
            "civic-db",
            "civic-adminer",
            "civic-internal-server",
        ]:
            container.stop()
    print_error("CIVIC Server stopped.")


# list_models()
# Lists all the models in the server by calling the API and printing the results in a table.
def list_models():
    print("Modules:")
    response = requests.get(f"{middleware_url}/get_models")
    response.raise_for_status()
    if response.json() == []:
        print_error("No models found.")
        return
    else:
        print_table(response.json())


# attach_to_server()
# Attaches to the server console by using the Docker attach command.
# It allows the user to interact with the internal server console.
def attach_to_server():
    try:
        # print("Attaching to the server. Press Ctrl+D to detach.")
        os.system('docker attach civic-internal-server --detach-keys="ctrl-d"')
        update_menu_state()  # Server may have been stopped
        print_menu(
            curr_menu,
            header=True,
        )
    except Exception as e:
        print_error(f"Failed to attach to the server: {e}")


# create_model()
# Creates a new model by prompting the user for the model details and uploading the model binary.
# It sends the model payload to the API middleware and handles the response.
def create_model():
    while True:
        model_name = input("Enter the name of the model: ").strip()
        if not model_name:
            print_error("Model name cannot be empty.")
        else:
            break
    model_display_name = input(
        "Enter the display name of the model (optional): "
    ).strip()
    if not model_display_name:
        model_display_name = model_name
    model_description = input(
        "Enter a short description of the model (optional): "
    ).strip()
    if not model_description:
        model_description = "n/a"

    while True:
        model_init_binary_path = input(
            "Enter the path to the initial model binary (v1): "
        ).strip()
        if not os.path.exists(model_init_binary_path):
            print_error("Model binary not found.")
        else:
            # Check if the file is a valid binary
            with open(model_init_binary_path, "rb") as f:
                binary_data = f.read()
                if not binary_data:
                    print_error("Model binary is empty.")
                else:
                    break

    # Create the model payload
    model_payload = {
        "name": model_name,
        "display_name": model_display_name,
        "description": model_description,
    }
    # Create model binary payload
    # Read and encode binary file
    with open(model_init_binary_path, "rb") as f:
        binary_data = f.read()
        encoded_data = base64.b64encode(binary_data).decode("utf-8")
    model_binary_payload = {
        "version": 1,
        "encoded_data": encoded_data,
    }

    # Send the model payload to the server
    print("Creating model...")
    response = requests.post(f"{middleware_url}/create_model", json=model_payload)
    response.raise_for_status()
    if response.status_code == 201:
        print_success("Model created successfully.")
        # Append the returned model ID to the payload
        model_binary_payload["model_id"] = response.json()["model_id"]
    else:
        print_error("Failed to create model.")

    # Send the model binary payload to the server
    print("Uploading model binary...")
    response = requests.post(
        f"{middleware_url}/upload_model_binary/{model_binary_payload['model_id']}",
        json=model_binary_payload,
    )
    response.raise_for_status()
    if response.status_code == 201:
        print_success("Model binary uploaded successfully.")
    else:
        print_error("Failed to upload model binary.")

    return


# select_model()
# Selects a model by prompting the user for the model ID.
def select_model(print_selection=True):
    # Check if there are any models
    response = requests.get(f"{middleware_url}/get_models")
    response.raise_for_status()
    if response.json() == []:
        print_error("No models found.")
        return -1

    # List the models
    list_models()
    while True:
        model_id = input("Select model by ID: ").strip()

        if not model_id:
            print_error("Model ID cannot be empty.")
            continue

        # Check if the model ID is valid
        response = requests.get(f"{middleware_url}/get_model/{model_id}")
        if response.json() != []:
            break
        else:
            print_error("Model ID not found.")
            continue

    # Get the model details
    response = requests.get(f"{middleware_url}/get_model/{model_id}")
    response.raise_for_status()
    model = response.json()
    if print_selection:
        print("Model details:")
        print_table(model)
    return model


# edit_model()
# Edits an existing model by prompting the user for the new model details.
# It sends the model payload to the API middleware and handles the response.
def edit_model():
    # Select model
    model = select_model()
    if model == -1:
        return
    # Get the new model details
    model_name = input(
        "Enter the new name of the model (leave blank to keep current): "
    ).strip()
    if not model_name:
        model_name = model[1]["name"]
    model_display_name = input(
        "Enter the new display name of the model (leave blank to keep current): "
    ).strip()
    if not model_display_name:
        model_display_name = model[1]["display_name"]
    model_description = input(
        "Enter the new description of the model (leave blank to keep current): "
    ).strip()
    if not model_description:
        model_description = model[1]["description"]

    # Create the model payload
    model_payload = {
        "name": model_name,
        "display_name": model_display_name,
        "description": model_description,
    }
    # Send the model payload to the server
    print("Editing model...")
    response = requests.put(
        f"{middleware_url}/edit_model/{model[1]["model_id"]}", json=model_payload
    )
    response.raise_for_status()
    if response.status_code == 200:
        print_success("Model edited successfully.")
    else:
        print_error("Failed to edit model.")
    return


# change_model_status()
# Changes the model status by prompting the user for the new model status.
# It sends the model status to the API middleware and handles the response.
def change_model_status():
    # Select model
    model = select_model()
    if model == -1:
        return
    # Get the new model status
    print(
        "Changing the model status indicates whether or not the server should be allowed to distribute the model to citizens. "
        "\nWhen the model is inactive, it will be unavailable for distribution, but the model will still be available for editing."
    )
    while True:
        model_status = (
            input("Enter the new status of the model (active/inactive): ")
            .strip()
            .lower()
        )
        if model_status not in ["active", "inactive"]:
            print_error("Invalid model status.")
            continue
        else:
            model_status = 1 if model_status == "active" else 0
            break
    # Call the API to change the model status
    print("Changing model status...")
    response = requests.put(
        f"{middleware_url}/change_model_status/{model[1]['model_id']}",
        json={"status": model_status},
    )
    response.raise_for_status()
    if response.status_code == 200:
        print_success("Model status changed successfully.")
    else:
        print_error("Failed to change model status.")
    return


# list_model_binaries()
# Lists all the model binaries for a specific model by calling the API and printing the results in a table.
def list_model_binaries():
    # Select model
    model = select_model(print_selection=False)
    if model == -1:
        return
    # Get all of the binaries for this model by id
    response = requests.get(
        f"{middleware_url}/get_model_binaries/{model[0]['model_id']}"
    )
    response.raise_for_status()
    if response.json() == []:
        print_error("No binaries found for this model.")
        return

    model_binaries = response.json()
    print("Model binaries:")
    print_table(model_binaries)
    return


# upload_model_binary()
# Uploads a new model binary by prompting the user for the new model binary path.
# Encodes the binary file in base64 and sends it to the API middleware.
def upload_model_binary():
    # Select model
    model = select_model(print_selection=False)
    if model == -1:
        return
    # Get all of the binaries for this model by id
    response = requests.get(
        f"{middleware_url}/get_model_binaries/{model[0]['model_id']}"
    )
    response.raise_for_status()
    if response.json() == []:
        print_error("No binaries found for this model.")
        return

    model_binaries = response.json()

    # Find the latest version
    latest_version = 0
    for binary in model_binaries:
        if binary["version"] > latest_version:
            latest_version = binary["version"]

    print(
        f"\nThe current binary version for this model is v{latest_version}. \
          \nFuture distributions of this model will use the provided v{latest_version+1} version of the binary.\n"
    )
    # Increment the version
    latest_version += 1
    # Get the new model binary path
    while True:
        model_binary_path = input(
            "Enter the path to the new model binary (v{}): ".format(latest_version)
        ).strip()
        if not os.path.exists(model_binary_path):
            print_error("Model binary not found.")
        else:
            # Check if the file is a valid binary
            with open(model_binary_path, "rb") as f:
                binary_data = f.read()
                if not binary_data:
                    print_error("Model binary is empty.")
                else:
                    break
    # Create the model binary payload
    # Read and encode binary file
    with open(model_binary_path, "rb") as f:
        binary_data = f.read()
        encoded_data = base64.b64encode(binary_data).decode("utf-8")
    model_binary_payload = {
        "version": latest_version,
        "encoded_data": encoded_data,
    }
    # Send the model binary payload to the server
    print("Uploading model binary...")

    response = requests.post(
        f"{middleware_url}/upload_model_binary/{model[0]['model_id']}",
        json=model_binary_payload,
    )
    response.raise_for_status()
    if response.status_code == 201:
        print_success("Model binary uploaded successfully.")
    else:
        print_error("Failed to upload model binary.")
    return


# create_dataset()
# Creates a new dataset by prompting the user for the dataset details.
# It sends the dataset payload to the API middleware and handles the response.
def create_dataset():
    list_models()
    model_id = input(
        "Enter the ID of the model you want to create the dataset for: "
    ).strip()

    # Check if there is a dataset for the model
    response = requests.get(f"{middleware_url}/dataset/{model_id}")
    if response.status_code == 200:
        if len(response.json()) > 0:
            print_error("Dataset already exists for this model.")
            override = (
                input("Do you want to override the existing dataset? [y/N]: ")
                .strip()
                .lower()
            )
            if override != "y":
                return

        # Ask for the type of dataset
        dataset_type = input("Enter the type of dataset [csv, json, txt]: ").strip()
        if dataset_type not in ["csv", "json", "txt"]:
            print_error("Invalid dataset type.")
            return

        # Ask for the dataset path
        dataset_path = input("Enter the path to the dataset: ").strip()
        if not os.path.exists(dataset_path):
            print_error("Dataset not found.")
            return

        # Open the dataset file
        try:
            with open(dataset_path, "r") as f:
                dataset = f.read()
                match dataset_type:
                    case "csv":
                        dataset = list(csv.DictReader(dataset.splitlines()))
                    case "json":
                        pass  # TODO
                    case "txt":
                        pass  # TODO
        except Exception as e:
            print_error(f"Failed to read the dataset: {e}")
            return

        # print(dataset)

        # Ask for how the dataset should be split
        print(
            "\nEach citizen will receive a split of the dataset when duties are assigned."
        )
        print(
            "The dataset will be split into equal parts, with the last split containing the remainder."
        )
        print(
            "For example, if there are 100 entries and 3 splits, each split will contain 33, 33, and 34 data entries."
        )
        print(
            "It is suggested to keep splits small to prevent overloading the clients, and for a better distribution of work.\n"
        )
        split = input(
            f"The imported dataset has a total of {len(dataset)} entries. Enter the number of splits (default 5/{len(dataset)}): "
        ).strip()
        split = int(split) if split else 5

        # Ask if the dataset should include replication
        print("\nOptionally, replication can be enabled for the dataset.")
        print("If enabled, the percentage of replication can be specified.")
        print(
            "For example, if 10% replication is specified, 10% of the dataset splits will be duplicated at random."
        )
        print("This can be useful for validating the results of the citizens.\n")
        replication = input(f"Enable replication? [y/N]: ").strip().lower()
        replication = replication == "y"
        replication_percentage = 0
        if replication:
            replication_percentage = input(
                "Enter the percentage of replication (default: 10%): "
            ).strip()
            replication_percentage = (
                int(replication_percentage) if replication_percentage else 10
            )

        # Ask if the dataset should be shuffled
        print("")
        shuffle = input("Should the dataset be shuffled? [y/N]: ").strip().lower()
        shuffle = shuffle == "y"

        # Create dataset payload
        dataset_payload = {
            "type": dataset_type,
            "data": dataset,
            "split": split,
            "replication": replication,
            "replication_percentage": replication_percentage,
            "shuffle": shuffle,
        }

        # Send the dataset payload to the server
        print("Creating dataset...")
        response = requests.post(
            f"{middleware_url}/create_dataset/{model_id}", json=dataset_payload
        )
        response.raise_for_status()
        if response.status_code == 201:
            print_success("Dataset created successfully.")
        else:
            print_error("Failed to create dataset.")

        return
    elif response.status_code != 404:
        print_error("Failed to check if dataset exists.")
        return


# safe_exit()
# Helper function to safely exit the program
def safe_exit():
    print("Exiting...")
    exit(0)


# signal_handler()
# Handles the SIGINT signal (Ctrl+C) and calls the safe_exit function
def signal_handler(sig, frame):
    safe_exit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
