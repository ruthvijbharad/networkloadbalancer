# client_work.py
import argparse, socket, random, itertools

def send_once(host, port, message):
    with socket.create_connection((host, port), timeout=5) as s, s.makefile('rwb') as f:
        f.write((message.rstrip("\n") + "\n").encode()); f.flush()
        resp = f.readline()
        return resp.decode().rstrip("\n") if resp else ""

DEFAULT_COMMANDS = [
    "ECHO hello load balancer",
    "UPPER make this uppercase",
    "REVERSE abcdefgh",
    "SUM 1 2 3 4 5",
    "SORT 5,3,9,1,7",
    "FACT 12",
    "FIB 20",
    "PRIME 97",
    "SLEEP 200",
    "STATS"
]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--commands", default="", help="semicolon-separated commands")
    ap.add_argument("--order", choices=["random","inorder"], default="random")
    args = ap.parse_args()

    cmds = [c.strip() for c in args.commands.split(";") if c.strip()] if args.commands else DEFAULT_COMMANDS

    if args.order == "inorder":
        it = itertools.cycle(cmds)
        for _ in range(args.count):
            msg = next(it)
            resp = send_once(args.host, args.port, msg)
            print(f"Client -> {msg!r} | Reply <- {resp!r}")
    else:
        for _ in range(args.count):
            msg = random.choice(cmds)
            resp = send_once(args.host, args.port, msg)
            print(f"Client -> {msg!r} | Reply <- {resp!r}")
