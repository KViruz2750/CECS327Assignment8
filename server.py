import socket
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def main():
    host = "0.0.0.0"  #listens on available network interfaces

    #setting db up
    print("=== Database Configuration ===")
    local_db_string = input("Enter NeonDB Connection String (postgresql://...): ").strip()
    peer_db_string = input("Enter Partner's NeonDB Connection String: ").strip()
    
    try:
        #this creates the SQLAlchemy engine for both local and partner databases
        local_engine = create_engine(local_db_string)
        peer_engine = create_engine(peer_db_string)
        
        #testing the connection for both dbs
        with local_engine.connect() as conn1, peer_engine.connect() as conn2:
            print("Success: Connected to BOTH NeonDB instances!\n")
            
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

                message_lower = message.lower()
                response = ""


                #---Routing Query Logic
                if "average moisture" in message_lower:
                    print("---> Routing to: Moisture Logic")
                    response = "Moisture Query recognized (db logic pending)."
                elif "water consumption" in message_lower:
                    print("--> Routing to: Water Consumption Logic")
                    response = "Water query recognized (db logic pending)."

                elif "electricity" in message_lower:
                    print("--> Routing to: Electricity Logic")
                    response = "Electricity query recognized (db logic pending)."
                else:
                    print("--> Unknown query received.")
                    response = "Error: Query not recognized."




                conn.sendall(response.encode("utf-8"))
                print(f"Sent to client: {response}")

    except OSError as e:
        print(f"Socket error: {e}")

    finally:
        server_socket.close()
        print("Server socket closed.")

if __name__ == "__main__":
    main()