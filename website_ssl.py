import SimpleHTTPServer
import SocketServer
import socket
import os
import ssl

WEBPORT = 443  # It's common to use port 443 for HTTPS
WEBDIRECTORY = "website"

class CustomHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = SimpleHTTPServer.SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(os.getcwd(), WEBDIRECTORY, relpath)
        return fullpath

def find_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# Automatically detect the IP
ip_address = find_ip()

# Set up a simple HTTP server and wrap it with SSL for HTTPS
httpd = SocketServer.TCPServer((ip_address, WEBPORT), CustomHandler)
httpd.socket = ssl.wrap_socket(httpd.socket, keyfile="key.pem", certfile="cert.pem", server_side=True)

web_address = "https://{}:{}".format(ip_address, WEBPORT)
print("Serving HTTPS at {}".format(web_address))
httpd.serve_forever()
