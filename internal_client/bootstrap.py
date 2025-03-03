import sys
import socket


def main():
    print_header()
    connect_to_server()


def print_header():
    print(
        Fore.LIGHTBLACK_EX
        + " "
        + "Python Internal Client".center(25, "-")
        + Style.RESET_ALL
        + "\n"
    )


def connect_to_server():
    print("Connecting to server...")

    # Create a socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


if __name__ == "__main__":
    main()
