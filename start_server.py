from apiserver import ApiServer, ApiRoute
import socket
import time
from multiprocessing import Process, Queue
import select
import sys
import requests
import logging
import json
import queue


q=Queue()

def post_send(msg):
    try:
        #res = requests.post('http://127.0.0.1:8200/api/services/device_key_service/rebroadcast', json={"tx_body":msg})
        res = requests.post('http://192.168.88.112:8200/api/services/device_key_service/rebroadcast', json={"tx_body":msg})
    
    except Exception:
        pass 

def post_send_subscribe(msg):
    res = requests.post('http://127.0.0.1:8100/api/services/device_key_service/subscribe', json={"tx_body":msg})

def get_wearout():
    res = requests.get('http://127.0.0.1:8200/api/services/device_key_service/get_short_device_key?public_key=91fc61fc1ed1856da51725f530951917ab5301d1c1f72a88a86c2950cb8f44ff')
    if res.ok:
        json_data = json.loads(res.text)
        s = json_data.get('wearout')
        return s
    else:
        return 1111111


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
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 5001 ))
    server.setblocking(0)
    server.listen(1024)
    addr = False
    inputs = [server] #Сокеты которые планируем читать
    outputs = []      #Сокеты в которые планируем писать
    message_queues = {}
    public_key_socket = {}

    while inputs:
        readable, writable, exceptional = select.select (inputs, outputs, inputs)
        #ЧТЕНИЕ
        for s in readable:
            if s is server:
                connection, client_address = s.accept()
                print(client_address)
                connection.setblocking(0)
                inputs.append(connection)
                outputs.append(connection)
                message_queues[connection] = queue.Queue()

            else:
                data = s.recv(1024)
                if data:
                    if data[0:7] == "404Code":
                        post_send_subscribe(data[7:])
                        public_key_socket[data[7:64]] = s
                        s.send(get_wearout(data[7:64]))
                    if data[0:7] == "410Code":
                        post_send(data[7:])
                else:
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    s.close()
                    del message_queues[s]
        #ЗАПИСЬ
        uslovie = True
        while uslovie:
            data = ""
            try:
                data = q.get(timeout = 0.001)
            except Exception:
                uslovie = False
            if data:
                public_key_socket.get(data[64:64]).send(data.encode())
        #ОШИБКИ
        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()
            del message_queues[s]



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
