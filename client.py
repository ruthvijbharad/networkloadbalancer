# client.py
import argparse, socket

def send_once(host, port, msg):
    with socket.create_connection((host, port), timeout=5) as s, s.makefile('rwb') as f:
        f.write((msg + "\n").encode()); f.flush()
        return f.readline().decode().strip()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--prefix", default="Req")
    args = ap.parse_args()
    for i in range(1, args.count + 1):
        msg = f"{args.prefix} #{i}"
        resp = send_once(args.host, args.port, msg)
        print(f"Client -> '{msg}' | Reply <- '{resp}'")
