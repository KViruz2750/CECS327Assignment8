# CECS 327 Assignment 8

Distributed TCP client/server application for answering a small set of smart-home analytics queries from PostgreSQL/Neon databases, with the TCP processes intended to run on GCP for the assignment deployment.

## What This Project Does

This repo contains:

- `server.py`: a TCP server intended to run on GCP, connect to two PostgreSQL-compatible databases, and answer analytics requests.
- `client.py`: a TCP client intended to run on GCP and send one of three supported natural-language queries to the server.
- `requirements.txt`: Python dependencies for the client/server runtime.

At a high level:

1. IoT devices publish data through DataNiz.
2. DataNiz-backed sensor data is stored in NeonDB/PostgreSQL.
3. The GCP-hosted server loads two database connection strings from environment variables.
4. The GCP-hosted client connects to the server over TCP and sends a supported query.
5. The server runs the matching SQL aggregation logic and returns a text response.

## Architecture

```text
+-----------+      device data      +------------------+
|  DataNiz  | --------------------> | Neon/PostgreSQL  |
+-----------+                       +------------------+
                                           ^
                                           | SQLAlchemy
                               +-----------+-----------+
                               |      GCP runtime      |
                               | +---------+  +------+ |
TCP request / response         | | client  |->|server| |
------------------------------>| +---------+  +------+ |
                               +-----------------------+
```

Assignment-level view:

- DataNiz is the ingestion side.
- NeonDB/PostgreSQL is the persisted sensor-data layer.
- The TCP client and TCP server run on GCP.
- This repo implements the TCP query path plus the database query logic.

The server uses the peer database only when the requested time window reaches back before the configured data-sharing start time.

## Supported Queries

The client only allows these exact strings:

1. `What is the average moisture inside our kitchen fridges in the past hours, week and month?`
2. `What is the average water consumption per cycle across our smart dishwashers in the past hour, week and month?`
3. `Which house consumed more electricity in the past 24 hours, and by how much?`

Important:

- Query matching in `client.py` is exact-string based.
- If you type a variation, the client will reject it before sending anything to the server.
- Copy/paste the query text from this README to avoid typos.

## Data Assumptions

The current implementation assumes both databases expose a table named `sensor_table_virtual` with fields compatible with the server queries.

Expected payload conventions:

- `payload->>'board_name'` identifies device type such as `fridge1`, `fridge2`, or `dishwasher`.
- `payload->>'Moisture'`, `payload->>'Moisture2'`, `payload->>'Moisture3'` store fridge moisture values.
- `payload->>'Flow'`, `payload->>'Flow2'`, `payload->>'Flow3'` store dishwasher water metrics.
- `payload->>'Ammeter'`, `payload->>'Ammeter2'`, `payload->>'Ammeter3'` store electricity metrics.
- `topic` is expected to include the house identifier as the first `/`-delimited segment.
- `time` is expected to be a timestamp column used for time-window filtering.

If your schema differs from those assumptions, the server logic will need code changes.

## Prerequisites

- Python 3.9+
- `pip`
- Access to two PostgreSQL/Neon databases
- A `.env` file in the project root with valid database connection strings

Python 3.9+ is required because the server uses `zoneinfo`.

## Configuration

Copy `.env.example` to `.env`, then replace the placeholder values:

```bash
cp .env.example .env
```

The file should contain:

```env
DB_URL_Connection_Khoi=postgresql://USERNAME:PASSWORD@HOST/DBNAME
DB_URL_Connection_Karan=postgresql://USERNAME:PASSWORD@HOST/DBNAME
```

Variable meaning:

| Variable | Purpose |
| --- | --- |
| `DB_URL_Connection_Khoi` | Database treated as the server's local data source |
| `DB_URL_Connection_Karan` | Database treated as the partner/peer data source |

The server also has a hard-coded sharing cutoff:

- `SHARING_START_TIME = 2026-04-18 10:00:00 America/Los_Angeles`

For long windows that start before that timestamp, the server supplements local results with peer data from before the sharing start time.

## Setup

### 1. Create and activate a virtual environment

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

## How To Run

For the assignment architecture, run both `server.py` and `client.py` on GCP. They can run on the same VM or on separate VMs, as long as the client can reach the server's listening port.

### Start the server

```bash
python server.py
```

Server startup flow:

1. Loads environment variables from `.env`
2. Connects to both databases
3. Prompts for a TCP port
4. Binds to `0.0.0.0:<port>` on the GCP host
5. Waits for one client connection

Example:

```text
Enter port number to listen on: 5000
Server is listening on port 5000...
```

### Start the client

Open a second terminal in the same project directory, activate the same virtual environment, then run:

```bash
python client.py
```

The client will prompt for:

- Server IP address or DNS name
- Server port number

Example:

```text
Enter server IP address: 10.128.0.15
Enter server port number: 5000
```

### Send a supported query

After the client connects, paste one of the three supported queries exactly as written above.

If both processes are on the same GCP VM, you can use:

```text
127.0.0.1
```

If they are on different GCP VMs, use the server VM's internal IP or external IP, depending on your network setup and firewall rules.

To disconnect:

```text
quit
```

## Example Session

Client:

```text
Enter server IP address: 10.128.0.15
Enter server port number: 5000
Connected to server.
Enter a message to send ('quit' to exit): What is the average moisture inside our kitchen fridges in the past hours, week and month?
Server response: Moisture Averages -> Hour: 51.23% | Week: 49.87% | Month: 50.04%
```

## Repository Layout

```text
.
├── client.py
├── server.py
├── requirements.txt
└── README.md
```

## Operational Notes

- The intended assignment deployment is GCP for both the TCP client and TCP server.
- The server handles a single accepted client connection for the lifetime of the process.
- The server uses blocking sockets; it is not concurrent or multi-client.
- Query routing on the server is keyword-based after the message arrives.
- The client receives responses with a single `recv(1024)`, which is fine for the current short text responses.
- There is no automated test suite in this repo today.

## GCP Deployment Notes

- If the server and client run on different GCP VMs, allow inbound traffic to the server port in the VM firewall or VPC firewall rule.
- The server listens on `0.0.0.0`, so it can accept connections from other hosts if the network allows it.
- Use the server VM's internal IP when both VMs are in the same VPC and that is allowed by your setup.
- Use the server VM's external IP only when required and permitted by firewall policy.
- NeonDB remains a managed external database service; it is not hosted by this repo.

## Troubleshooting

### Database connection fails on server startup

Check:

- `.env` exists in the project root
- both connection strings are valid
- the target databases are reachable from your machine
- required tables and columns exist

### Client says the query cannot be processed

Cause:

- The client only accepts the three exact supported query strings.

Fix:

- Copy/paste the query text directly from the README.

### Client cannot connect to server

Check:

- the server process is already running
- the IP address is correct
- the port number matches the server port
- the GCP VM firewall allows inbound traffic on that port
- local firewall settings are not blocking the connection

### Server returns incomplete electricity comparison

Cause:

- The query needs data for at least two houses in the last 24 hours.

Fix:

- Verify both databases contain recent data with correctly formatted `topic` values.

## Deactivate the Virtual Environment

```bash
deactivate
```
