import socket


def main():
    #prompt user for server IP
    server_ip = input("Enter server IP address: ").strip()

    #prompt user for server port
    while True:
        try:
            server_port = int(input("Enter server port number: "))
            if 0 <= server_port <= 65535:
                break
            print("Error: Port number must be between 0 and 65535.")
        except ValueError:
            print("Error: Please enter a valid integer for the port.")

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((server_ip, server_port))
        print("Connected to server.")

        while True:
            message = input("Enter a message to send ('quit' to exit): ")

            if message.lower() == "quit":
                print("Closing connection.")
                break

            client_socket.sendall(message.encode("utf-8"))

            response = client_socket.recv(1024).decode("utf-8")
            print(f"Server response: {response}")

    except ValueError:
        print("Error: Invalid IP address or port number.")
    except socket.gaierror:
        print("Error: Invalid server IP address.")
    except ConnectionRefusedError:
        print("Error: Connection refused. Make sure the server is running.")
    except TimeoutError:
        print("Error: Connection timed out.")
    except OSError as e:
        print(f"Socket error: {e}")

    finally:
        client_socket.close()
        print("Client socket closed.")


if __name__ == "__main__":
    main()