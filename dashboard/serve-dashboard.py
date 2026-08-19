#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import argparse, os
ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8080);ap.add_argument('--bind',default='0.0.0.0');args=ap.parse_args()
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(f'Dashboard available on http://{args.bind}:{args.port}')
ThreadingHTTPServer((args.bind,args.port),SimpleHTTPRequestHandler).serve_forever()
