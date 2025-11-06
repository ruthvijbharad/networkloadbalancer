# server.py (enhanced: executes real tasks)
import argparse
import socket
import threading
import time

REQ_LIMITS = {"FACT": 20000, "FIB": 1000000}

def parse_numbers(s):
    parts = [p.strip() for p in s.replace(",", " ").split() if p.strip()]
    return [float(p) if "." in p else int(p) for p in parts]

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    r = int(n**0.5)
    f = 3
    while f <= r:
        if n % f == 0:
            return False
        f += 2
    return True

def fib(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def fact(n: int) -> int:
    res = 1
    for i in range(2, n+1):
        res *= i
    return res

def handle(conn, addr, name, counter):
    try:
        with conn, conn.makefile('rwb') as f:
            line = f.readline()
            if not line:
                return
            raw = line.decode().rstrip('\n')
            start = time.time()
            parts = raw.strip().split(maxsplit=1)
            cmd = parts[0].upper() if parts else ""
            arg = parts[1] if len(parts) > 1 else ""
            try:
                if cmd == "ECHO":
                    result = arg
                elif cmd == "UPPER":
                    result = arg.upper()
                elif cmd == "REVERSE":
                    result = arg[::-1]
                elif cmd == "SUM":
                    nums = parse_numbers(arg)
                    result = str(sum(nums))
                elif cmd == "SORT":
                    nums = parse_numbers(arg)
                    result = " ".join(map(str, sorted(nums)))
                elif cmd == "FACT":
                    n = int(arg.strip() or "0")
                    n = min(n, REQ_LIMITS["FACT"])
                    result = str(fact(n))
                elif cmd == "FIB":
                    n = int(arg.strip() or "0")
                    n = min(n, 100000)
                    result = str(fib(n))
                elif cmd == "PRIME":
                    n = int(arg.strip() or "0")
                    result = "YES" if is_prime(n) else "NO"
                elif cmd == "SLEEP":
                    ms = int(arg.strip() or "0")
                    time.sleep(max(0, ms) / 1000.0)
                    result = f"Slept {ms} ms"
                elif cmd == "STATS":
                    result = f"requests_handled={counter['count']}"
                else:
                    result = raw
            except Exception as ex:
                result = f"ERROR processing command: {ex}"
            counter['count'] += 1
            dur_ms = int((time.time() - start) * 1000)
            reply = f"{name} ok: {cmd or 'ECHO'} => {result} (took {dur_ms} ms)\n".encode()
            f.write(reply); f.flush()
    except Exception as e:
        print(f"[{name}] Error handling {addr}: {e}")

def serve(host, port, name):
    print(f"[{name}] starting on {host}:{port}")
    counter = {'count': 0}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle, args=(conn, addr, name, counter), daemon=True).start()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--name", default="Server")
    args = ap.parse_args()
    serve(args.host, args.port, args.name)
