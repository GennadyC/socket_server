from apiserver import ApiServer, ApiRoute
import socket
import time
from multiprocessing import Process, Queue
import select
import sys
import requests
import json
import queue
import logging


q=Queue()

def post_send(msg):
    try:
        res = requests.post('http://127.0.0.1:8200/api/services/device_key_service/rebroadcast', json={"tx_body":msg})
        return "Ok"
        logging.info(b'POST short_key Ok')
    except Exception:
        logging.info(b'Client close')
        return "Close" 

def post_send_subscribe(msg):
    try:
        res = requests.post('http://127.0.0.1:8100/api/services/device_key_service/subscribe', json={"tx_body":msg})
        return "Ok"
    except Exception:
        logging.info(b'Client close')
        return "Close"
        
def get_wearout(msg):
    try:
        res = requests.get('http://127.0.0.1:8200/api/services/device_key_service/get_short_device_key?public_key='+msg)
        if res.ok:
            json_data = json.loads(res.text)
            s = json_data.get('wearout')
            return s
        else:
            return 1111111
    except Exception:
        logging.info(b'Client close')
        return "Close"


class MyServer(ApiServer):
    def __init__(self, addr, port, q):
        ApiServer.__init__(self, addr, port)

    @ApiRoute("/")
    def addbar(req):
        q.put(str(req["tx_body"]))
        logging.info(b'Post from Exonum')
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
    inputs = [server] 
    outputs = []      
    message_queues = {}
    public_key_socket = {}

    while inputs:
        readable, writable, exceptional = select.select (inputs, outputs, inputs)

        for s in readable:
            if s is server:
                connection, client_address = s.accept()
                logging.info(client_address)
                connection.setblocking(0)
                inputs.append(connection)
                outputs.append(connection)
                message_queues[connection] = queue.Queue()

            else:
                try:
                    data_encode = s.recv(1024)
                    data = data_encode.decode()
                except Exception:
                    data = ""
                if data:
                    if data[0:7] == "404Code":
                        logging.info(b'Message from client with 404Code')
                        r = post_send_subscribe(data[7:])
                        if r == "Close":
                            try:
                                inputs.remove(s)
                                if s in outputs:
                                    outputs.remove(s)
                                s.close()
                                del message_queues[s]
                                del public_key_socket[data[7:71]]
                            except Exception:
                                pass
                        public_key_socket[data[7:71]] = s
                        wearout = get_wearout(data[7:71])
                        if wearout == "Close":
                            try:
                                inputs.remove(s)
                                if s in outputs:
                                    outputs.remove(s)
                                s.close()
                                del message_queues[s]
                                del public_key_socket[data[7:71]]
                            except Exception:
                                pass
                            
                        else:
                            s.send(str(wearout).encode())
                    if data[0:7] == "410Code":
                        logging.info(b'Message from client with 410Code')
                        p = post_send(data[7:])
                        if p == "Close":
                            try:
                                inputs.remove(s)
                                if s in outputs:
                                    outputs.remove(s)
                                s.close()
                                del message_queues[s]
                                del public_key_socket[data[64:128]]
                            except Exception:
                                pass
                else:
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    s.close()
                    del message_queues[s]
        uslovie = True
        while uslovie:
            data = ""
            try:
                data = q.get(timeout = 0.001)
            except Exception:
                uslovie = False
            if data:
                try:
                    public_key_socket[data[64:128]].send(data.encode())
                except Exception:
                    pass
        for s in exceptional:
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()
            del message_queues[s]



def serv(q):
    MyServer("0.0.0.0",5000, q).serve_forever()

def main():
    logging.basicConfig(format = u'%(levelname)-8s [%(asctime)s] %(message)s', level = logging.INFO, filename = u'SocketLog.log')

    s = Process(target=serv, args=(q,))
    a = Process(target=sock, args=(q,))
    s.start()
    a.start()
    s.join()
    a.join()


if __name__ == "__main__":
    main()
