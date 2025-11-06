# Round-Robin Load Balancer — Full Bundle with Live Dashboard

## Files
- `server.py` — Enhanced backend worker (ECHO, SUM, SORT, FACT, FIB, PRIME, SLEEP, STATS)
- `load_balancer.py` — Core round-robin balancer
- `client.py` — Simple tester
- `client_work.py` — Smart client (random or in-order mode)
- `load_balancer_dashboard.py` — Balancer + live dashboard (no external libs)
- `README.md` — This file

## How to run

### 1) Start backend servers
python server.py --port 9001 --name Server-A
python server.py --port 9002 --name Server-B
python server.py --port 9003 --name Server-C

### 2) Start the balancer (no dashboard)
python load_balancer.py --port 9000 --backends 127.0.0.1:9001,127.0.0.1:9002,127.0.0.1:9003

### (or) Start the balancer with dashboard
python load_balancer_dashboard.py --port 9000 --backends 127.0.0.1:9001,127.0.0.1:9002,127.0.0.1:9003 --dash-port 8080

Open: http://127.0.0.1:8080/

### 3) Generate traffic
python client_work.py --port 9000 --count 12 --order random
# or in exact sequence
python client_work.py --port 9000 --commands "SUM 1 2 3 4; FACT 10; PRIME 97; SLEEP 200; UPPER hello" --order inorder --count 5
