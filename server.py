import socket
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

SHARING_START_TIME = datetime(2026, 4, 18, 10, 0, 0) #year month day hour minute seconddef fetch_sensor_stats(engine, board_names, sensor_key, interval_str, before_time=None):

def fetch_sensor_stats(engine, board_names, sensor_key, interval_str, before_time=None):
    """Helper function to get the SUM and COUNT of a JSON sensor value"""
    sql = f"""
        SELECT 
            SUM(
                COALESCE((payload->>'{sensor_key}')::numeric, 0) +
                COALESCE((payload->>'{sensor_key}2')::numeric, 0) +
                COALESCE((payload->>'{sensor_key}3')::numeric, 0)
            ) as total_sum,
            COUNT(*) as total_count
        FROM sensor_table_virtual
        WHERE payload->>'board_name' IN :board_names 
        AND time >= NOW() - CAST(:interval AS INTERVAL)
    """
    
    #if we need missing history from the peer, ONLY grabs data from before sharing started
    if before_time:
        sql += f" AND time < '{before_time.strftime('%Y-%m-%d %H:%M:%S')}'"
        
    query = text(sql)
    
    with engine.connect() as conn:
        result = conn.execute(query, {
            "board_names": tuple(board_names), 
            "interval": interval_str
        }).fetchone()
        
        total_sum = float(result[0]) if result and result[0] is not None else 0.0
        total_count = int(result[1]) if result and result[1] is not None else 0
        return total_sum, total_count
    
    
def process_moisture_query(local_engine, peer_engine):
    """Calculates the distributed average for the past hour, week, and month."""
    """Answers Query #1"""
    board_names = ("fridge1", "fridge2")
    sensor_key = "Moisture"     
    
    intervals = {"hour": "1 hour", "week": "7 days", "month": "30 days"}
    results = []

    for label, sql_interval in intervals.items():
        #1. fetch data from local database
        local_sum, local_count = fetch_sensor_stats(local_engine, board_names, sensor_key, sql_interval)
        total_sum, total_count = local_sum, local_count
        
        #2. check if we need to fetch missing data from partner'S database
        now = datetime.now()
        if label == "hour": delta = timedelta(hours=1)
        elif label == "week": delta = timedelta(days=7)
        else: delta = timedelta(days=30)
        
        interval_start_time = now - delta
        
        #if the query goes further back than when we started sharing, this will grab the missing data
        if interval_start_time < SHARING_START_TIME:
            print(f"[{label}] Missing peer data detected. Querying partner database...")
            peer_sum, peer_count = fetch_sensor_stats(peer_engine, board_names, sensor_key, sql_interval, before_time=SHARING_START_TIME)
            total_sum += peer_sum
            total_count += peer_count
            
        #3. calculate the final average
        if total_count > 0:
            avg = total_sum / total_count
            results.append(f"{label.capitalize()}: {avg:.2f}%")
        else:
            results.append(f"{label.capitalize()}: No data")

    return "Moisture Averages -> " + " | ".join(results)

def process_water_query(local_engine, peer_engine):
    """Calculates the distributed average water consumption for dishwashers."""
    """Answers Query 2, and almost identical to query 1 code"""
    
    board_names = ("dishwasher",) 
    
    sensor_key = "Flow" 
    
    intervals = {"hour": "1 hour", "week": "7 days", "month": "30 days"}
    results = []

    for label, sql_interval in intervals.items():
        #1. fetch local data
        local_sum, local_count = fetch_sensor_stats(local_engine, board_names, sensor_key, sql_interval)
        total_sum, total_count = local_sum, local_count
        
        #2. checking for missing peer history
        now = datetime.now()
        if label == "hour": delta = timedelta(hours=1)
        elif label == "week": delta = timedelta(days=7)
        else: delta = timedelta(days=30)
        
        interval_start_time = now - delta
        
        if interval_start_time < SHARING_START_TIME:
            print(f"[{label}] Missing peer data detected. Querying partner database...")
            peer_sum, peer_count = fetch_sensor_stats(peer_engine, board_names, sensor_key, sql_interval, before_time=SHARING_START_TIME)
            total_sum += peer_sum
            total_count += peer_count
            
        #3. calculate final average
        if total_count > 0:
            avg = total_sum / total_count
            results.append(f"{label.capitalize()}: {avg:.2f} gallons")
        else:
            results.append(f"{label.capitalize()}: No data")

    return "Water Consumption Averages -> " + " | ".join(results)



def process_electricity_query(local_engine, peer_engine):
    """Calculates total 24-hour electricity by summing specific Ammeters across all appliances."""
    
    house_totals = {}

    #1. fetch from LOCAL database
    local_sql = text("""
        SELECT 
            SPLIT_PART(topic, '/', 1) as house_email,
            SUM(
                COALESCE((payload->>'Ammeter')::numeric, 0) +
                COALESCE((payload->>'Ammeter2')::numeric, 0) +
                COALESCE((payload->>'Ammeter3')::numeric, 0)
            ) as total_electricity
        FROM sensor_table_virtual
        WHERE time >= NOW() - INTERVAL '24 hours'
        GROUP BY SPLIT_PART(topic, '/', 1)
    """)
    
    with local_engine.connect() as conn:
        local_results = conn.execute(local_sql).fetchall()
        for email, total in local_results:
            house_totals[email] = house_totals.get(email, 0.0) + float(total)

    #2. fetch missing history from peer database
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
    
    if twenty_four_hours_ago < SHARING_START_TIME:
        print("[24 Hours] Missing historical peer data. Querying partner database...")
        peer_sql = text("""
            SELECT 
                SPLIT_PART(topic, '/', 1) as house_email,
                SUM(
                    COALESCE((payload->>'Ammeter')::numeric, 0) +
                    COALESCE((payload->>'Ammeter2')::numeric, 0) +
                    COALESCE((payload->>'Ammeter3')::numeric, 0)
                ) as total_electricity
            FROM sensor_table_virtual
            WHERE time >= NOW() - INTERVAL '24 hours'
            AND time < :sharing_start
            GROUP BY SPLIT_PART(topic, '/', 1)
        """)
        
        with peer_engine.connect() as conn:
            peer_results = conn.execute(peer_sql, {
                "sharing_start": SHARING_START_TIME.strftime('%Y-%m-%d %H:%M:%S')
            }).fetchall()
            for email, total in peer_results:
                house_totals[email] = house_totals.get(email, 0.0) + float(total)

    #3. calculate the difference and format output
    if len(house_totals) < 2:
        return "Error: Could not find electricity data for both houses in the last 24 hours. Ensure both are sending data."

    houses = list(house_totals.keys())
    house1_email, house1_total = houses[0], house_totals[houses[0]]
    house2_email, house2_total = houses[1], house_totals[houses[1]]

    if house1_total > house2_total:
        higher_house, higher_val = house1_email, house1_total
        lower_house, lower_val = house2_email, house2_total
    else:
        higher_house, higher_val = house2_email, house2_total
        lower_house, lower_val = house1_email, house1_total

    difference = higher_val - lower_val

    return (f"In the past 24 hours, {higher_house} consumed more electricity "
            f"({higher_val:.2f} Amps) compared to {lower_house} ({lower_val:.2f} Amps). "
            f"The difference is {difference:.2f} Amps.")




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
                    response = process_moisture_query(local_engine, peer_engine)
                elif "water consumption" in message_lower:
                    print("--> Routing to: Water Consumption Logic")
                    response = process_water_query(local_engine, peer_engine)

                elif "electricity" in message_lower:
                    print("--> Routing to: Electricity Logic")
                    response = process_electricity_query(local_engine, peer_engine)
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