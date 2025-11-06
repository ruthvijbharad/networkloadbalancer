# load_balancer_dashboard.py
import argparse
import socket
import threading
import json
import time
from collections import Counter, deque
from typing import List, Tuple
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

class RoundRobin:
    def __init__(self, backends: List[Tuple[str, int]]):
        self.backends = backends[:]
        self.i = 0
        self.lock = threading.Lock()
    def next(self) -> Tuple[str, int]:
        with self.lock:
            addr = self.backends[self.i]
            self.i = (self.i + 1) % len(self.backends)
            return addr

class State:
    def __init__(self, backends: List[Tuple[str,int]], max_events: int = 100):
        self.counts = Counter({tuple(b): 0 for b in backends})
        self.events = deque(maxlen=max_events)
        self.lock = threading.Lock()
        self.backends = [tuple(b) for b in backends]
    def record(self, client_addr, backend, msg):
        with self.lock:
            self.counts[tuple(backend)] += 1
            self.events.appendleft({
                "t": time.strftime("%H:%M:%S"),
                "client": f"{client_addr[0]}:{client_addr[1]}",
                "backend": f"{backend[0]}:{backend[1]}",
                "msg": msg
            })
    def snapshot(self):
        with self.lock:
            return {
                "counts": {f"{h}:{p}": self.counts[(h,p)] for (h,p) in self.backends},
                "events": list(self.events),
                "backends": [f"{h}:{p}" for (h,p) in self.backends],
                "time": time.time()
            }

DASHBOARD_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>LB Dashboard</title>
<style>
body{font-family:system-ui,Segoe UI,Roboto,sans-serif;margin:20px}
.row{display:flex;gap:20px;flex-wrap:wrap}
.card{border:1px solid #ddd;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.counts{min-width:360px}
.bar{height:22px;background:#e5e7eb;border-radius:6px;overflow:hidden;margin:6px 0 12px}
.bar>div{height:100%;background:#60a5fa}
table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid #eee;padding:8px 10px;text-align:left;font-size:14px}
th{background:#fafafa;position:sticky;top:0}
.muted{color:#6b7280;font-size:12px}
</style></head>
<body>
<h2>Round-Robin Load Balancer — Live Dashboard</h2>
<div class="muted">Refreshes every second. Shows per-backend counts and recent requests.</div>
<div class="row">
  <div class="card counts"><h3>Per-backend counts</h3><div id="bars"></div></div>
  <div class="card" style="flex:1;min-width:420px">
    <h3>Recent requests</h3>
    <div style="max-height:380px;overflow:auto">
      <table><thead><tr><th>Time</th><th>Client</th><th>Backend</th><th>Message</th></tr></thead><tbody id="events"></tbody></table>
    </div>
  </div>
</div>
<script>
async function refresh(){
 try{
   const r=await fetch('/stats'); const d=await r.json();
   const total=Object.values(d.counts).reduce((a,b)=>a+b,0)||1;
   let bars=''; for(const b of d.backends){const c=d.counts[b]||0; const w=Math.round((c/total)*100);
     bars+=`<div><div><b>${b}</b> — ${c}</div><div class="bar"><div style="width:${w}%"></div></div></div>`}
   document.getElementById('bars').innerHTML=bars;
   let ev=''; for(const e of d.events){ev+=`<tr><td>${e.t}</td><td>${e.client}</td><td>${e.backend}</td><td>${e.msg}</td></tr>`}
   document.getElementById('events').innerHTML=ev;
 }catch(e){console.error(e)}
}
refresh(); setInterval(refresh,1000);
</script>
</body></html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    state: State = None
    def do_GET(self):
        if self.path in ("/","/index.html"):
            c=DASHBOARD_HTML.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(c))); self.end_headers(); self.wfile.write(c); return
        if self.path=="/stats":
            snap=self.state.snapshot(); p=json.dumps(snap).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(p)))
            self.end_headers(); self.wfile.write(p); return
        self.send_response(404); self.end_headers()

def start_dashboard(state, host, port):
    class Handler(DashboardHandler): pass
    Handler.state=state
    httpd=ThreadingHTTPServer((host,port),Handler)
    t=threading.Thread(target=httpd.serve_forever,daemon=True); t.start()
    print(f"[LB] dashboard at http://{host}:{port}/")

def forward_to_backend(backend,data:bytes)->bytes:
    host,port=backend
    with socket.create_connection((host,port),timeout=5) as s, s.makefile('rwb') as f:
        f.write(data); f.flush(); return f.readline() or b""

def handle_client(conn,addr,rr,state):
    try:
        with conn, conn.makefile('rwb') as f:
            line=f.readline()
            if not line: return
            msg=line.decode().strip()
            backend=rr.next()
            resp=forward_to_backend(backend,line)
            f.write(resp); f.flush()
            state.record(addr,backend,msg)
            print(f"[LB] {addr} -> {backend} : {msg}")
    except Exception as e:
        print(f"[LB] error {addr}: {e}")

def run_lb(lh,lp,backends,dh,dp):
    state=State(backends); start_dashboard(state,dh,dp)
    rr=RoundRobin(backends)
    print(f"[LB] listening on {lh}:{lp}")
    print(f"[LB] backends: {', '.join([f'{h}:{p}' for h,p in backends])}")
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        s.bind((lh,lp)); s.listen()
        while True:
            conn,addr=s.accept()
            threading.Thread(target=handle_client,args=(conn,addr,rr,state),daemon=True).start()

def parse_backends(spec:str):
    out=[]
    for part in spec.split(","):
        host,port=part.strip().split(":"); out.append((host,int(port)))
    if not out: raise ValueError("No backends")
    return out

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--host",default="127.0.0.1")
    ap.add_argument("--port",type=int,default=9000)
    ap.add_argument("--backends",required=True)
    ap.add_argument("--dash-host",default="127.0.0.1")
    ap.add_argument("--dash-port",type=int,default=8080)
    a=ap.parse_args()
    run_lb(a.host,a.port,parse_backends(a.backends),a.dash_host,a.dash_port)
