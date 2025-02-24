# communicates with servers
# has list of downloadable models from server
# handles downloading of models
# docker setup (create citizen) based on model

import os
import argparse
import requests
import docker
import time
import json
from colorama import Fore, Style, init
from enum import Enum
import signal

VERSION = "v0.1.0"

menu_options = [
    [  # Global commands (0)
        {"key": "h", "command": "Help", "status": 1},
        {"key": "e", "command": "Exit", "status": 1},
        ### Hidden globals
        {"key": "help", "command": "h_help", "status": -1},
        {"key": "clear", "command": "h_clear", "status": -1},
        {"key": "exit", "command": "h_exit", "status": -1},
    ],
    [  # Main menu (1)
        {"key": "c", "command": "Connect to CIVIC Server", "status": 1},
        {"key": "mc", "command": "Manage Citizens", "status": 1},
    ],
    [  # Manage Citizens (2)
        {"key": "l", "command": "List Citizens", "status": 1},
        {"key": "c", "command": "Create Citizen", "status": 1},
        {"key": "d", "command": "Delete Citizen", "status": 1},
        {"key": "b", "command": "Back", "status": 1},
    ],
]
menu_states = Enum("Menu", ["GLOBAL", "MAIN", "MANAGE_CITIZENS"], start=0)
menu_state_titles = ["Global Commands", "Main Menu", "Manage Citizens"]
curr_menu = menu_states.MAIN


def main():
    os.system("clear")
    print_header()

    init_client()

    global curr_menu
    print_menu(curr_menu)

    while True:
        choice = input("$ ").lower()

        ### Global commands (0)

        if any(choice == item["key"] for item in menu_options[0]):
            match choice:
                case "h":
                    print_menu(curr_menu)
                case "e":
                    safe_exit()
                # Hidden commands
                case "help":
                    print_menu(curr_menu)
                case "exit":
                    safe_exit()
                case "clear":
                    os.system("clear")

        ### Main Menu (1)

        elif curr_menu == menu_states.MAIN:
            match choice:
                case "c":
                    print("Connecting to CIVIC Server...\n")  # TODO
                case "mc":
                    set_curr_menu(menu_states.MANAGE_CITIZENS)
                case _:
                    print_error("Invalid command. Please try again.")

        ### Manage Citizens (2)

        elif curr_menu == menu_states.MANAGE_CITIZENS:
            match choice:
                case "l":
                    print("Listing Citizens...\n")  # TODO
                case "c":
                    print("Creating Citizen...\n")  # TODO
                case "d":
                    print("Deleting Citizen...\n")  # TODO
                case "b":
                    set_curr_menu(menu_states.MAIN)
                case _:
                    print_error("Invalid command. Please try again.")


def set_curr_menu(menu_index):
    global curr_menu
    curr_menu = menu_index
    print_menu(curr_menu)


def print_header():
    header = "CIVIC Client {}".format(Fore.YELLOW + VERSION)
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


def init_client():
    print("Initializing client...")  # TODO


def safe_exit():
    print("Exiting...")
    exit(0)


def signal_handler(sig, frame):
    safe_exit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
