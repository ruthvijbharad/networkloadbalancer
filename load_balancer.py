# load_balancer.py
import argparse, socket, threading
from typing import List, Tuple

class RoundRobin:
    def __init__(self, backends: List[Tuple[str, int]]):
        self.backends = backends
        self.i = 0
        self.lock = threading.Lock()
    def next(self) -> Tuple[str, int]:
        with self.lock:
            addr = self.backends[self.i]
            self.i = (self.i + 1) % len(self.backends)
            return addr

def forward_to_backend(backend, data: bytes) -> bytes:
    host, port = backend
    with socket.create_connection((host, port), timeout=5) as s, s.makefile('rwb') as f:
        f.write(data); f.flush()
        return f.readline() or b""

def handle_client(conn, addr, rr: RoundRobin):
    try:
        with conn, conn.makefile('rwb') as f:
            line = f.readline()
            if not line:
                return
            backend = rr.next()
            resp = forward_to_backend(backend, line)
            f.write(resp); f.flush()
            print(f"[LB] {addr} -> {backend} : {line.decode().strip()}")
    except Exception as e:
        print(f"[LB] error {addr}: {e}")

def run_lb(host, port, backends):
    rr = RoundRobin(backends)
    print(f"[LB] listening on {host}:{port}")
    print(f"[LB] backends: {', '.join([f'{h}:{p}' for h, p in backends])}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr, rr), daemon=True).start()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--backends", required=True)
    args = ap.parse_args()
    backends = [tuple(x.split(":")) for x in args.backends.split(",")]
    backends = [(h, int(p)) for h, p in backends]
    run_lb(args.host, args.port, backends)
