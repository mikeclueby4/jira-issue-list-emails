#!/usr/bin/env python
"""
Runs a HTTP server for enhanced/dynamic versions of jira-issue-list-emails
"""
from http.server import HTTPServer,BaseHTTPRequestHandler
from urllib import parse
from myutils import *
from typing import List
import argparse
import makereport
import settings
from markupsafe import Markup,escape

isearch

class MyHandler(BaseHTTPRequestHandler):

    def ret200(self):
        self.send_response(200)
        self.send_header('Content-Type',
                        'text/html; charset=utf-8')
        self.end_headers()

    def outhtml(self, html):
        self.wfile.write(html.encode('utf-8'))


    def do_GET(self):
        parsed_path = parse.urlparse(self.path)

        if parsed_path.path=="/":
            self.frontpage()
            return

        m = re.match(r"""/report/([^/]+)/?(.*)""", parsed_path.path)
        if m:
            # m.group(2) is future extension
            report = m.group(1)
            if report in settings.reports:
                html = settings.reports[report]()
                self.ret200()
                self.outhtml(html)
                return

        # 404!
        message_parts = [
            r"""
 ,------.,------. ,------.  ,-----. ,------.           .---.    .----.      .---.
 |  .---'|   /`. '|   /`. '|  .-.  '|   /`. '         / .  |   /  ..  \    / .  |
 |  |    |  /  | ||  /  | ||  | |  ||  /  | |        / /|  |  .  /  \  .  / /|  |
 |  '--. |  |_.' ||  |_.' ||  | |  ||  |_.' |       / / |  |_ |  |  '  | / / |  |_
 |  .--' |  .  '.'|  .  '.'|  | |  ||  .  '.'      /  '-'    |'  \  /  '/  '-'    |
 |  `---.|  |\  \ |  |\  \ |  '-'  ||  |\  \       `----|  |-' \  `'  / `----|  |-'
 `------'`--' '--'`--' '--' `-----' `--' '--'           `--'    `---''       `--'

"""
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
                '{}={}'.format(name, str(value).rstrip())
            )
        message_parts.append('')
        message = '\r\n'.join(message_parts)
        self.send_response(404)
        self.send_header('Content-Type',
                         'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(message.encode('utf-8'))

    def frontpage(self):
        self.ret200()
        self.outhtml(makereport.getheader(title="Reports available", mybasehref=""))
        self.outhtml("""
Reports available:
<ul>
""")
        for name,_ in settings.reports.items():
            self.outhtml(Markup("""
<li><a href="/report/{name}">{name}</a></li>
""").format(name=name))

        self.outhtml("""
</ul>""")
        self.outhtml(makereport.getfooter())




def serve(addrport):
    httpd = HTTPServer((args.listen,args.port), MyHandler)
    print(f"Starting HTTP server on {addrport}")
    httpd.serve_forever()
    print("Server died?!")


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

    serve((args.listen,args.port))
