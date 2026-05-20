import sys
import os

VIRTUALENV = '/home/qqwtlphb/virtualenv/backend/3.13'
activate_this = os.path.join(VIRTUALENV, 'bin/activate_this.py')
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

sys.path.insert(0, '/home/qqwtlphb/backend')

from dotenv import load_dotenv
load_dotenv('/home/qqwtlphb/backend/.env')

import asyncio
from main import app as fastapi_app


def application(environ, start_response):
    headers = []
    for key, value in environ.items():
        if key.startswith('HTTP_'):
            name = key[5:].lower().replace('_', '-')
            headers.append((name.encode(), value.encode()))
        elif key == 'CONTENT_TYPE' and value:
            headers.append((b'content-type', value.encode()))
        elif key == 'CONTENT_LENGTH' and value:
            headers.append((b'content-length', value.encode()))

    body = b''
    try:
        length = int(environ.get('CONTENT_LENGTH', 0))
        if length > 0:
            body = environ['wsgi.input'].read(length)
    except:
        pass

    scope = {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'method': environ['REQUEST_METHOD'],
        'headers': headers,
        'path': environ.get('PATH_INFO', '/'),
        'query_string': environ.get('QUERY_STRING', '').encode(),
        'root_path': environ.get('SCRIPT_NAME', ''),
        'server': (environ.get('SERVER_NAME', 'localhost'), int(environ.get('SERVER_PORT', 80))),
    }

    response_started = []
    response_body = []

    async def receive():
        return {'type': 'http.request', 'body': body, 'more_body': False}

    async def send(message):
        if message['type'] == 'http.response.start':
            response_started.append(message)
        elif message['type'] == 'http.response.body':
            response_body.append(message.get('body', b''))

    asyncio.run(fastapi_app(scope, receive, send))

    status_code = response_started[0]['status']
    resp_headers = response_started[0].get('headers', [])

    status = f'{status_code} OK'
    out_headers = [(k.decode() if isinstance(k, bytes) else k, v.decode() if isinstance(v, bytes) else v) for k, v in resp_headers]
    start_response(status, out_headers)
    return response_body
