import socket
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def main():
    host = "0.0.0.0"  #listens on available network interfaces

    #setting db up
    print("=== Database Configuration ===")
    db_string = input("Enter NeonDB Connection String (postgresql://...): ").strip()
    
    try:
        #this creates the SQLAlchemy engine
        engine = create_engine(db_string)
        
        #testing the connection immediately to catch errors early
        with engine.connect() as db_conn:
            print("Success: Connected to NeonDB!\n") #since we are connecting to neonDB
            
    except SQLAlchemyError as e:
        print(f"Database connection error: {e}")
        print("Exiting setup. Please check your connection string.")
        return #stopping the execution if the DB fails to connect

    #tcp server
    print("=== TCP Server Configuration ===")
    while True:
        try:
            port = int(input("Enter port number to listen on: "))
            if 0 <= port <= 65535:
                break
            print("Error: Port number must be between 0 and 65535.")
        except ValueError:
            print("Error: Please enter a valid integer for the port.")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"Server is listening on port {port}...")

        conn, addr = server_socket.accept()
        print(f"Connected by {addr[0]}:{addr[1]}")

        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    print("Client disconnected.")
                    break

                message = data.decode("utf-8")
                print(f"Received from client: {message}")

                response = f"SERVER ACK: {message.upper()}"
                conn.sendall(response.encode("utf-8"))
                print(f"Sent to client: {response}")

    except OSError as e:
        print(f"Socket error: {e}")

    finally:
        server_socket.close()
        print("Server socket closed.")

if __name__ == "__main__":
    main()