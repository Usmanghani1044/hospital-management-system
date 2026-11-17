# Author: Muhammad Usman Ghani
# Project: Hospital Management
# Course: Database Systems
"""Start the local educational dashboard: python3 main.py"""
import argparse
import json
import secrets
import sqlite3
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from hospital.service import Hospital

ROOT=Path(__file__).resolve().parent


def make_handler(service,token):
    class Handler(BaseHTTPRequestHandler):
        def reply(self,status,body,content_type='application/json',filename=None):
            if isinstance(body,dict):body=json.dumps(body).encode()
            if isinstance(body,str):body=body.encode()
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            self.end_headers();self.wfile.write(body)

        def permitted(self,api=False):
            host=self.headers.get('Host','').split(':')[0]
            if host not in ('127.0.0.1','localhost'):
                self.reply(403,{'error':'Use localhost or 127.0.0.1.'});return False
            if api and not secrets.compare_digest(self.headers.get('X-Demo-Token',''),token):
                self.reply(403,{'error':'Reload this local page before continuing.'});return False
            return True

        def do_GET(self):
            path=urlparse(self.path).path
            if not self.permitted(path.startswith('/api/')):return
            try:
                if path=='/':
                    html=(ROOT/'static/index.html').read_text(encoding='utf-8').replace('__TOKEN__',token)
                    self.reply(200,html,'text/html; charset=utf-8')
                elif path in ('/app.js','/style.css'):
                    self.reply(200,(ROOT/'static'/path[1:]).read_bytes(),'text/javascript' if path.endswith('.js') else 'text/css')
                elif path=='/api/state':self.reply(200,service.snapshot())
                elif path.startswith('/api/export/'):
                    name=path.rsplit('/',1)[1];self.reply(200,service.export(name),'text/csv; charset=utf-8',f'{name}.csv')
                elif path=='/api/backup':
                    with tempfile.TemporaryDirectory() as tmp:
                        destination=Path(tmp)/'hospital-backup.sqlite3';service.backup(destination)
                        self.reply(200,destination.read_bytes(),'application/octet-stream','hospital-backup.sqlite3')
                else:self.reply(404,{'error':'Not found.'})
            except ValueError as exc:self.reply(400,{'error':str(exc)})
            except sqlite3.Error:self.reply(503,{'error':'Database busy or unavailable. Try again.'})

        def do_POST(self):
            if not self.permitted(True):return
            if urlparse(self.path).path!='/api/action':self.reply(404,{'error':'Not found.'});return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=32768:raise ValueError('Request must be 1–32,768 bytes.')
                data=json.loads(self.rfile.read(length))
                if not isinstance(data,dict) or not isinstance(data.get('payload'),dict):raise ValueError('Invalid request.')
                identifier=service.act(data.get('action'),data['payload'])
                self.reply(200,{'id':identifier,'message':f'Saved successfully. Record #{identifier}.'})
            except (ValueError,TypeError,AttributeError) as exc:self.reply(400,{'error':str(exc)})
            except sqlite3.Error:self.reply(503,{'error':'Database busy or unavailable. Try again.'})

        def log_message(self,format,*args):
            # Avoid logging entered patient data; this is a local demo.
            pass
    return Handler


def main():
    parser=argparse.ArgumentParser(description='Hospital Management local educational dashboard')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--db',type=Path,default=ROOT/'runtime/hospital.sqlite3')
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--check',action='store_true',help='Check foreign keys and database integrity, then exit')
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Port must be between 1 and 65535.')
    if sqlite3.sqlite_version_info < (3,31,0):
        print('SQLite 3.31+ is required. Use a newer Python installation.');return 1
    service=Hospital(args.db);created=service.initialize()
    if args.check:
        c=service.connect()
        try:
            integrity=c.execute('PRAGMA integrity_check').fetchone()[0];foreign=c.execute('PRAGMA foreign_key_check').fetchall()
            print(f'Integrity: {integrity}; foreign-key violations: {len(foreign)}')
            return 0 if integrity=='ok' and not foreign else 1
        finally:c.close()
    try:server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(service,secrets.token_urlsafe(32)))
    except OSError:
        print('Port unavailable. Try: python3 main.py --port 8766');return 1
    url=f'http://127.0.0.1:{args.port}'
    print('\nHOSPITAL MANAGEMENT | Muhammad Usman Ghani')
    print('Fictional educational demo. No login or production security: do not enter real patient data.')
    print('Demo database created.' if created else 'Existing database loaded; your changes are preserved.')
    print(f'Open: {url}\nDatabase: {args.db}\nStop with Control+C.\n')
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:print('\nServer stopped. Data remains saved.')
    finally:server.server_close()
    return 0


if __name__=='__main__':raise SystemExit(main())
