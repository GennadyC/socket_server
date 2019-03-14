import sys, json
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse
import threading
import logging
log = logging.getLogger(__name__)

class ApiError(Exception):
    def __init__(self, code, msg=None, desc=None):
        self.code = code
        self.msg = msg
        self.desc = desc

    def __str__(self):
        return f"ApiError({self.code}, {self.msg})"

def ApiRoute(path):
    def outer(func):
        if not hasattr(func, "_routes"):
            setattr(func, "_routes", [])
        func._routes += [path]
        return func
    return outer

class ApiServer(HTTPServer):
    def __init__(self, addr, port):
        server_address = (addr, port)
        self.__addr = addr
        class handler_class(ApiHandler):
            pass

        self.handler_class = handler_class

        for meth in type(self).__dict__.values():
            if hasattr(meth, "_routes"):
                for route in meth._routes:
                    self.add_route(route, meth)

        super().__init__(server_address, handler_class)

    def add_route(self, path, meth):
        self.handler_class._routes[path] = meth
        
    def port(self):
        sa = self.socket.getsockname()
        return sa[1]

    def address(self):
        sa = self.socket.getsockname()
        return sa[0]

    def uri(self, path):
        if path[0] == "/":
            path = path[1:]
        return "http://"+self.__addr + ":"+ str(self.port()) + "/" + path

    def shutdown(self):
        super().shutdown()
        self.socket.close()

class ApiHandler(BaseHTTPRequestHandler):
    _routes={}


    def do_GET(self):
        self.do_XXX()

    def do_POST(self):
        content="{}"
        if self.headers["Content-Length"]:
            length = int(self.headers["Content-Length"])
            content=self.rfile.read(length)
        info=None
        if content:
            try:
                info = json.loads(content)
            except:
                raise ApiError(400, "Invalid JSON", content)
        self.do_XXX(info)

    def do_XXX(self, info={}):
        try:
            url=urlparse.urlparse(self.path)

            handler = self._routes.get(url.path)

            if url.query:
                params = urlparse.parse_qs(url.query)
            else:
                params = {}

            info.update(params)

            if handler:
                try:
                    response=handler(info)
                    self.send_response(200)
                    if response is None:
                        response = ""
                    if type(response) is dict:
                        response = json.dumps(response)
                    response = bytes(str(response),"utf-8")
                    self.send_header("Content-Length", len(response))
                    self.end_headers()
                    self.wfile.write(response)
                except ApiError:
                    raise
                except ConnectionAbortedError as e:
                    log.error(f"GET {self.path} : {e}")
                except Exception as e:
                    raise ApiError(500, str(e))
            else:
                raise ApiError(404)
        except ApiError as e:
            try:
                self.send_error(e.code, e.msg, e.desc)
            except ConnectionAbortedError as e:
                log.error(f"GET {self.path} : {e}")


