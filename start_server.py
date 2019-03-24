from apiserver import ApiServer, ApiRoute
import socket
import time
from multiprocessing import Process, Queue
import select
import socket
import sys
import requests
import logging
import json

q=Queue()

def post_send(msg):
    res = requests.post('http://127.0.0.1:8200/api/services/device_key_service/rebroadcast', json={"tx_body":msg})

def post_send_subscribe(msg):
    res = requests.post('http://127.0.0.1:8100/api/services/device_key_service/subscribe', json={"tx_body":msg})

#def post_send_register(msg):
#    res = requests.post('http://127.0.0.1:8200/api/services/device_key_service/unsubscribe', json={"tx_body":msg})

def get_send():
    res = requests.get('http://127.0.0.1:8200/api/services/device_key_service/get_short_device_key?public_key=91fc61fc1ed1856da51725f530951917ab5301d1c1f72a88a86c2950cb8f44ff')
    if res.ok:
        json_data = json.loads(res.text)
        s = json_data.get('wearout')
        return s
    else:
        return 1111111

def get_send_register():
    res = requests.get('http://127.0.0.1:8100/api/services/device_key_service/get_subscriber?public_key=91fc61fc1ed1856da51725f530951917ab5301d1c1f72a88a86c2950cb8f44ff')
    if (res.text == 'Subscriber PublicKey(91fc61fc...) not found'):
        result = 'no'
        return result
    else:
        result = 'yes'
        return result


class MyServer(ApiServer):
    def __init__(self, addr, port, q):
        ApiServer.__init__(self, addr, port)

    @ApiRoute("/")
    def addbar(req):
        q.put(str(req["tx_body"]))
        #return {"tx_body":req["tx_body"]+1}

    @ApiRoute("/baz")
    def justret(req):
        if req:
            raise ApiError(501,"no data in for baz")
        return {"obj":1}

def sock(q):
    timeout = 10.0
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 5001 ))
    #s.setblocking(0)
    s.listen(0)
    addr=False
    while True:
        cli = False
        try:
            client, addr = s.accept()
        except socket.error:
            continue
        client.settimeout(timeout)
        try:
            content = client.recv(1024)
        except socket.error:
            continue
        sub=False
        if (content.decode("utf-8") == 'Subscribe'):
            sub = get_send_register()
            if sub == 'yes':
                client.send(str(sub).encode())
            if sub == 'no':
                client.send(str(sub).encode())
                try:
                   content = client.recv(1024)
                except socket.error:
                    continue
                post_send_subscribe(content.decode("utf-8"))
        
        status = False
        try:
            content = client.recv(1024)
        except socket.error:
            continue
        if (content.decode("utf-8") == 'Register'):
            status = get_send()
        client.send(str(status).encode())
        try:
            content = client.recv(1024)
            post_send(content.decode("utf-8"))
            cli = True
        except Exception:
            cli = False
        while cli:
            try:
                k=q.get(timeout=5)
                if k:
                    client.send(k.encode())
                    k=0
                    try:
                        content = client.recv(1024)
                        post_send(content.decode("utf-8"))
                    except Exception:
                        cli = False
            except Exception as error:
                break
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
