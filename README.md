# CECS327Assignment8

TCP client/server assignment with NeonDB connectivity.

## Prerequisites

- Python 3.10+
- pip
- A NeonDB connection string for each peer database

## Create and Activate a Virtual Environment

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run the Server

```bash
python server.py
```

When prompted, enter:

- Your NeonDB connection string
- Partner NeonDB connection string
- TCP port to listen on

## Run the Client

Open another terminal in the same folder, activate the same virtual environment, then run:

```bash
python client.py
```

When prompted, enter:

- Server IP address
- Server port number

The client accepts only these exact three queries:

1. What is the average moisture inside our kitchen fridges in the past hours, week and month?
2. What is the average water consumption per cycle across our smart dishwashers in the past hour, week and month?
3. Which house consumed more electricity in the past 24 hours, and by how much?

Any other input is rejected with a user-friendly message.

## Deactivate Environment

```bash
deactivate
```
