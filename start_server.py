from apiserver import ApiServer, ApiRoute
import socket
import time
from multiprocessing import Process, Queue
import select
import socket 
import sys
import requests

q=Queue()

def post_send(msg):
    #res = requests.post('http://46.241.87.38:8200/api/services/device_key_service/rebroadcast', json={"tx_body":msg})
    res = requests.post('http://0.0.0.0:8200//api/services/device_key_service/rebroadcast', json={"tx_body":msg})
    if res.ok:
        print (res.json())

def post_send1(msg):
    #res = requests.post('http://46.241.87.38:8200/api/services/device_key_service/rebroadcast', json={"tx_body":msg})
    res = requests.post('http://0.0.0.0:8200/api/services/device_key_service/rebroadcast', json={"tx_body":msg})
    if res.ok:
        print (res.json())

class MyServer(ApiServer): 
    def __init__(self, addr, port, q):
        ApiServer.__init__(self, addr, port)

    @ApiRoute("/")
    def addbar(req):
        print(req["tx_body"])
        q.put(str(req["tx_body"]))
        #print(q.get())
        return {"tx_body":req["tx_body"]+1}

    @ApiRoute("/baz")
    def justret(req):
        if req:
            raise ApiError(501,"no data in for baz")
        return {"obj":1}

def sock(q):
    timeout = 2.0
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 5001 ))
    s.listen(5)
    addr=False                 
    while True:
        print("teper tut")
        client, addr = s.accept()
        print("eto ya")
        client.settimeout(timeout)

        while client:
            #print(addr)
            
            try:
                k=q.get(timeout=2.0)
                if k:
                    client.send(k.encode())
                    k=0
            except Exception as error:
                print("POST_Non")
            try:
                content = client.recv(1024)
                if content[73:76] == "0000":
                    post_send1(content)
                    print("VSE SKAZAL")
                else:
                    post_send(content)
                    print("VSE SKAZAL")
            except Exception:
                print("Non")
        print("YA TUT")
        time.sleep(1)
        client.settimeout(None)

        client.close()

def serv(q):
    MyServer("0.0.0.0",5000, q).serve_forever()

def main():

    s = Process(target=serv, args=(q,))
    a = Process(target=sock, args=(q,))

    s.start()
    a.start()
    s.join()
    a.join()


if __name__ == "__main__":
    main()

