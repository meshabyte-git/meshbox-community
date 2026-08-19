#!/usr/bin/env python3
import argparse, html, json, os, platform, re, shutil, socket, subprocess, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

VERSION = '1.0.0'
DEFAULT_CONFIG = '/etc/community-dashboard-agent/config.json'
TELEMETRY_KEYS = ['cpu','memory','storage','uptime','network_speed','operating_system','ip_address','tailscale_ip']

def load_config(path):
    with open(path, 'r', encoding='utf-8') as f: cfg=json.load(f)
    cfg.setdefault('agent', {})
    cfg['agent'].setdefault('bind','0.0.0.0'); cfg['agent'].setdefault('port',9876)
    cfg['agent'].setdefault('status_page',True); cfg['agent'].setdefault('cors_origins',['*'])
    cfg.setdefault('telemetry',{})
    for k in TELEMETRY_KEYS: cfg['telemetry'].setdefault(k, True if k!='tailscale_ip' else False)
    return cfg

def read_first(path, default=''):
    try:
        with open(path,'r',encoding='utf-8',errors='ignore') as f: return f.read().strip()
    except Exception: return default

def esc(v): return html.escape(str(v), quote=True)
def fmt_bytes(n):
    if n is None: return '—'
    n=float(n)
    for u in ['B','KB','MB','GB','TB','PB']:
        if abs(n)<1024: return f'{n:.1f} {u}' if u!='B' else f'{int(n)} B'
        n/=1024
    return f'{n:.1f} EB'

def os_info():
    data={}
    for line in read_first('/etc/os-release').splitlines():
        if '=' in line:
            k,v=line.split('=',1); data[k]=v.strip().strip('"')
    return {'name':data.get('PRETTY_NAME') or data.get('NAME') or platform.system(),'id':data.get('ID',''),'version':data.get('VERSION_ID',''),'architecture':platform.machine()}

def cpu_snapshot():
    vals=[int(x) for x in read_first('/proc/stat').splitlines()[0].split()[1:]]
    return vals[3]+(vals[4] if len(vals)>4 else 0), sum(vals)

def cpu_percent(interval=.15):
    try:
        i1,t1=cpu_snapshot(); time.sleep(interval); i2,t2=cpu_snapshot(); dt=t2-t1
        return round(100*(1-(i2-i1)/dt),1) if dt else 0.0
    except Exception: return None

def cpu_model():
    for line in read_first('/proc/cpuinfo').splitlines():
        if line.lower().startswith('model name') and ':' in line: return line.split(':',1)[1].strip()
    return platform.processor() or 'Unknown'

def memory_info():
    mem={}
    for line in read_first('/proc/meminfo').splitlines():
        if ':' in line:
            k,v=line.split(':',1); m=re.search(r'(\d+)',v)
            if m: mem[k]=int(m.group(1))*1024
    total=mem.get('MemTotal',0); avail=mem.get('MemAvailable',mem.get('MemFree',0)); used=max(total-avail,0)
    return {'total_bytes':total,'used_bytes':used,'available_bytes':avail,'percent':round(100*used/total,1) if total else 0}

def storage_info():
    pseudo={'proc','sysfs','devtmpfs','devpts','tmpfs','cgroup','cgroup2','overlay','squashfs','tracefs','securityfs','pstore','debugfs','mqueue','hugetlbfs','fusectl','configfs','ramfs','autofs','nsfs','rpc_pipefs'}
    mounts=[]; seen=set()
    for line in read_first('/proc/mounts').splitlines():
        p=line.split()
        if len(p)<3: continue
        dev,mnt,fstype=p[:3]; mnt=mnt.replace('\\040',' ')
        if fstype in pseudo or mnt in seen or not mnt.startswith('/'): continue
        try:
            u=shutil.disk_usage(mnt)
            if u.total<=0: continue
            mounts.append({'device':dev,'mount':mnt,'filesystem':fstype,'total_bytes':u.total,'used_bytes':u.used,'free_bytes':u.free,'percent':round(100*u.used/u.total,1)}); seen.add(mnt)
        except Exception: pass
    return sorted(mounts,key=lambda x:(x['mount']!='/',x['mount']))

def human_duration(sec):
    d,sec=divmod(sec,86400); h,sec=divmod(sec,3600); m,_=divmod(sec,60); parts=[]
    if d: parts.append(f'{d}d')
    if h: parts.append(f'{h}h')
    if m or not parts: parts.append(f'{m}m')
    return ' '.join(parts)

def uptime_info():
    try: sec=int(float(read_first('/proc/uptime').split()[0]))
    except Exception: sec=0
    return {'seconds':sec,'human':human_duration(sec)}

def interface_bytes():
    out={}
    for line in read_first('/proc/net/dev').splitlines()[2:]:
        if ':' not in line: continue
        name,data=line.split(':',1); vals=data.split()
        if len(vals)>=16: out[name.strip()]={'rx':int(vals[0]),'tx':int(vals[8])}
    return out

def network_speed(interval=.25):
    a=interface_bytes(); t=time.monotonic(); time.sleep(interval); b=interface_bytes(); delta=max(time.monotonic()-t,.001)
    interfaces=[]; rx=tx=0
    for name,cur in b.items():
        if name=='lo' or name not in a: continue
        dr=max(cur['rx']-a[name]['rx'],0); dtx=max(cur['tx']-a[name]['tx'],0); rx+=dr; tx+=dtx
        interfaces.append({'interface':name,'rx_bytes_per_sec':round(dr/delta),'tx_bytes_per_sec':round(dtx/delta)})
    return {'rx_bytes_per_sec':round(rx/delta),'tx_bytes_per_sec':round(tx/delta),'interfaces':interfaces}

def local_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('192.0.2.1',80)); ip=s.getsockname()[0]; s.close(); return ip
    except Exception:
        try: return socket.gethostbyname(socket.gethostname())
        except Exception: return None

def tailscale_ip():
    try:
        p=subprocess.run(['tailscale','ip','-4'],capture_output=True,text=True,timeout=2)
        if p.returncode==0 and p.stdout.strip(): return p.stdout.strip().splitlines()[0]
    except Exception: pass
    return None

def collect(cfg):
    enabled=cfg['telemetry']; data={'hostname':socket.gethostname(),'timestamp':int(time.time()),'agent_version':VERSION,'telemetry_enabled':enabled.copy()}
    if enabled.get('cpu'): data['cpu']={'model':cpu_model(),'logical_cpus':os.cpu_count(),'percent':cpu_percent()}
    if enabled.get('memory'): data['memory']=memory_info()
    if enabled.get('storage'): data['storage']=storage_info()
    if enabled.get('uptime'): data['uptime']=uptime_info()
    if enabled.get('network_speed'): data['network_speed']=network_speed()
    if enabled.get('operating_system'): data['operating_system']=os_info()
    if enabled.get('ip_address'): data['ip_address']=local_ip()
    if enabled.get('tailscale_ip'): data['tailscale_ip']=tailscale_ip()
    return data

def gauge(label,value,detail=''):
    try: n=max(0,min(float(value),100)); val=f'{n:.0f}%'
    except Exception: n=0; val='—'
    tone='danger' if n>=80 else ('warn' if n>=65 else 'normal')
    return f'''<div class="gauge-wrap"><div class="gauge {tone}" style="--p:{n}"><div><strong>{val}</strong><span>{esc(label)}</span></div></div><small>{esc(detail)}</small></div>'''

def status_html(data):
    gauges=[]
    if 'cpu' in data:
        c=data['cpu']; gauges.append(gauge('CPU',c.get('percent'),f"{c.get('logical_cpus','?')} logical CPUs"))
    if 'memory' in data:
        m=data['memory']; gauges.append(gauge('Memory',m.get('percent'),f"{fmt_bytes(m.get('used_bytes'))} / {fmt_bytes(m.get('total_bytes'))}"))
    if data.get('storage'):
        r=next((x for x in data['storage'] if x['mount']=='/'),data['storage'][0]); gauges.append(gauge('Storage',r.get('percent'),f"{fmt_bytes(r.get('used_bytes'))} / {fmt_bytes(r.get('total_bytes'))}"))
    cards=[]
    if gauges: cards.append('<section class="panel gauge-panel">'+''.join(gauges)+'</section>')
    if 'network_speed' in data:
        n=data['network_speed']; cards.append(f'''<section class="panel"><div class="section-head"><h2>Network</h2><span>Live throughput</span></div><div class="network"><div><span>Download / RX</span><strong>↓ {fmt_bytes(n['rx_bytes_per_sec'])}/s</strong></div><div><span>Upload / TX</span><strong>↑ {fmt_bytes(n['tx_bytes_per_sec'])}/s</strong></div></div></section>''')
    facts=[]
    if 'uptime' in data: facts.append(('Uptime',data['uptime']['human']))
    if 'operating_system' in data: facts.append(('Operating System',data['operating_system']['name']))
    if 'ip_address' in data: facts.append(('IP Address',data.get('ip_address') or 'Unavailable'))
    if 'tailscale_ip' in data: facts.append(('Tailscale IP',data.get('tailscale_ip') or 'Unavailable'))
    if facts: cards.append('<section class="panel"><div class="section-head"><h2>System</h2><span>Enabled telemetry only</span></div><div class="facts">'+''.join(f'<div><span>{esc(k)}</span><strong>{esc(v)}</strong></div>' for k,v in facts)+'</div></section>')
    if 'storage' in data and len(data['storage'])>1:
        rows=''.join(f'<div class="storage-row"><span>{esc(x["mount"])}</span><span>{fmt_bytes(x["used_bytes"])} / {fmt_bytes(x["total_bytes"])}</span><strong>{x["percent"]}%</strong></div>' for x in data['storage'])
        cards.append(f'<section class="panel"><div class="section-head"><h2>Storage</h2><span>Mounted filesystems</span></div>{rows}</section>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(data['hostname'])} · System Status</title><style>
:root{{--bg:#e9edf2;--panel:#f4f6f8;--raised:#fff;--text:#17202a;--muted:#66727e;--line:#cdd4dc;--accent:#3478d4;--good:#278c54;--warn:#c48120;--danger:#c63e47;--shadow:0 8px 24px rgba(23,32,42,.07)}}@media(prefers-color-scheme:dark){{:root{{--bg:#09121d;--panel:#111d2a;--raised:#162435;--text:#eef3f8;--muted:#9ba9b7;--line:#293a4d;--accent:#62a4ff;--good:#44cc7a;--warn:#e1a842;--danger:#ff6670;--shadow:none}}}}html[data-theme=light]{{--bg:#e9edf2;--panel:#f4f6f8;--raised:#fff;--text:#17202a;--muted:#66727e;--line:#cdd4dc;--accent:#3478d4;--good:#278c54;--warn:#c48120;--danger:#c63e47;--shadow:0 8px 24px rgba(23,32,42,.07)}}html[data-theme=dark]{{--bg:#09121d;--panel:#111d2a;--raised:#162435;--text:#eef3f8;--muted:#9ba9b7;--line:#293a4d;--accent:#62a4ff;--good:#44cc7a;--warn:#e1a842;--danger:#ff6670;--shadow:none}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}header{{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:20px}}h1{{margin:0;font-size:28px}}.subtitle{{display:flex;align-items:center;gap:8px;color:var(--muted);margin-top:5px}}.dot{{width:8px;height:8px;border-radius:50%;background:var(--good);display:inline-block}}button{{border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:10px;padding:9px 12px;cursor:pointer}}.panel{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:16px;box-shadow:var(--shadow)}}.gauge-panel{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:18px}}.gauge-wrap{{text-align:center}}.gauge{{--ring:var(--accent);width:142px;aspect-ratio:1;margin:auto;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--ring) calc(var(--p)*1%),var(--line) 0);position:relative}}.gauge:before{{content:"";position:absolute;inset:12px;border-radius:50%;background:var(--panel)}}.gauge>div{{z-index:1;display:grid}}.gauge strong{{font-size:27px}}.gauge span,.gauge-wrap small,.section-head span,.facts span,.network span{{color:var(--muted);font-size:13px}}.gauge.warn{{--ring:var(--warn)}}.gauge.danger{{--ring:var(--danger)}}.section-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}}h2{{font-size:17px;margin:0}}.network{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.network>div,.facts>div{{background:var(--raised);border:1px solid var(--line);border-radius:11px;padding:14px}}.network strong{{display:block;font-size:21px;margin-top:5px}}.facts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}}.facts strong{{display:block;margin-top:4px;overflow-wrap:anywhere}}.storage-row{{display:grid;grid-template-columns:1fr 2fr 70px;gap:12px;padding:10px 0;border-bottom:1px solid var(--line)}}.storage-row:last-child{{border-bottom:0}}.storage-row strong{{text-align:right}}footer{{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:12px;padding:4px}}@media(max-width:620px){{main{{padding:18px}}.network{{grid-template-columns:1fr}}.storage-row{{grid-template-columns:1fr}}.storage-row strong{{text-align:left}}}}
</style></head><body><main><header><div><h1>{esc(data['hostname'])}</h1><div class="subtitle"><span class="dot"></span> ONLINE · System Status</div></div><button id="theme" type="button" aria-label="Toggle light and dark mode">◐ Theme</button></header>{''.join(cards)}<footer><span>Read-only local status page</span><span>Agent {VERSION} · refreshed every 5 seconds</span></footer></main><script>(function(){{const h=document.documentElement,b=document.getElementById('theme'),saved=localStorage.getItem('status-theme');if(saved)h.dataset.theme=saved;b.addEventListener('click',()=>{{const now=h.dataset.theme||((matchMedia('(prefers-color-scheme:dark)').matches)?'dark':'light');const next=now==='dark'?'light':'dark';h.dataset.theme=next;localStorage.setItem('status-theme',next)}});setTimeout(()=>location.reload(),5000)}})()</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    server_version='CommunityDashboardAgent/1.0'
    def _cors(self):
        origin=self.headers.get('Origin',''); allowed=self.server.cfg['agent'].get('cors_origins',['*']); val='*' if '*' in allowed else (origin if origin in allowed else '')
        if val: self.send_header('Access-Control-Allow-Origin',val)
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.send_header('Access-Control-Allow-Methods','GET, OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type'); self.end_headers()
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/health': body=b'{"status":"ok"}'; ctype='application/json'
        elif path=='/api/status': body=json.dumps(collect(self.server.cfg),separators=(',',':')).encode(); ctype='application/json'
        elif path=='/status' and self.server.cfg['agent'].get('status_page',True): body=status_html(collect(self.server.cfg)).encode(); ctype='text/html; charset=utf-8'
        else: self.send_error(404); return
        self.send_response(200); self.send_header('Content-Type',ctype); self._cors(); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,fmt,*args): print('%s - %s'%(self.address_string(),fmt%args))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',default=DEFAULT_CONFIG); args=ap.parse_args(); cfg=load_config(args.config); addr=(cfg['agent']['bind'],int(cfg['agent']['port']))
    srv=ThreadingHTTPServer(addr,Handler); srv.cfg=cfg; print(f'Community Dashboard Agent {VERSION} listening on {addr[0]}:{addr[1]}')
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
if __name__=='__main__': main()
