#!/usr/bin/env python
"""
Runs a HTTP server for enhanced/dynamic versions of jira-issue-list-emails
"""
from http.server import HTTPServer,BaseHTTPRequestHandler
from urllib import parse
import argparse

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed_path = parse.urlparse(self.path)
        message_parts = [
            'CLIENT VALUES:',
            'client_address={} ({})'.format(
                self.client_address,
                self.address_string()),
            'command={}'.format(self.command),
            'path={}'.format(self.path),
            'real path={}'.format(parsed_path.path),
            'query={}'.format(parsed_path.query),
            'request_version={}'.format(self.request_version),
            '',
            'SERVER VALUES:',
            'server_version={}'.format(self.server_version),
            'sys_version={}'.format(self.sys_version),
            'protocol_version={}'.format(self.protocol_version),
            '',
            'HEADERS RECEIVED:',
        ]
        for name, value in sorted(self.headers.items()):
            message_parts.append(
                '{}={}'.format(name, value.rstrip())
            )
        message_parts.append('')
        message = '\r\n'.join(message_parts)
        self.send_response(200)
        self.send_header('Content-Type',
                         'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--listen",
        default="0.0.0.0",
        metavar="IPADDR",
        help="IP to server requests on (default:all addresses)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=81,
        help="Port to listen on (default:81 - since we assume Jira to be on port 80/443)",
    )
    args = parser.parse_args()

    httpd = HTTPServer((args.listen,args.port), MyHandler)
    print(f"Starting HTTP server on {args.listen}:{args.port}")
    httpd.serve_forever()
    print("Server died?!")
