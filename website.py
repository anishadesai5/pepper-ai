import SimpleHTTPServer
import SocketServer
import socket
import os

'''
FYI : You would run this to setup the web server but main.py also has this setup.
'''

#chattxt.pepper.com
WEBPORT = 8081
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

httpd = SocketServer.TCPServer((ip_address, WEBPORT), CustomHandler)

web_address = "http://{}:{}".format(ip_address, WEBPORT)
print("Serving at {}".format(web_address))
httpd.serve_forever()
