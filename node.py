"""
Node.py

En este fichero se encuentra el nodo comunicativo de la blockchain.
Estos nodos componen la red P2P, siendo efectivamente los «peers» de
esta.
"""

import json

from multiprocessing import Process
from threading import Thread
from pprint import pformat
from random import randint
from time import sleep
from uuid import uuid4

import zmq

CONNECT_FORMAT_STR = "{protocol}://{address}:{port}"
PROTOCOL = "tcp"

class Node:

    def __init__(self, port):
        self.uuid = uuid4()
        self.context = zmq.Context()
        #: Elige un puerto efímero aleatorio
        # self.port = randint(49152, 65535)
        self.port = str(port)
        self.message_queue = []
        #self.p = Process(target=self.handle_messages, args=(self.message_queue,))
        self.p = Thread(target=self.handle_messages)
        self.p.start()
        self.publish_queue = []
        self.t = Thread(target=self.publish_thread)
        self.t.start()

    def jsonize(self):
        # TODO: En realidad esto es más convertir a dict que a json,
        # las funciones que hacen referencia a json supongo deberían
        # devolver objetos json de una vez.
        return {
            "uuid": self.uuid,
            "port": self.port
        }

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return pformat(self.jsonize(), indent=1, width=80)

    def send_message(self, message: bytes, address: str, port: int):
        socket = self.context.socket(zmq.DEALER)
        #socket.connect("tcp://127.0.0.1:5555")# + str(self.port))
        socket.connect(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address=address,
            port=str(port)
        ))
        socket.send(b"", zmq.SNDMORE)
        socket.send(message)
        #socket.recv()
        socket.close()

    def handle_messages(self):
        rep_socket = self.context.socket(zmq.REP)
        rep_socket.bind(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address="*",
            port=self.port
        ))
        sub_socket = self.context.socket(zmq.SUB)
        sub_socket.bind(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address="*",
            port=str(int(self.port) + 1)
        ))
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        poller = zmq.Poller()
        poller.register(rep_socket, zmq.POLLIN)
        poller.register(sub_socket, zmq.POLLIN)
        try:
            while True:
                #message = socket.recv()
                #socket.send(b"READY")
                #self.update_message_queue(message)
                messages = dict(poller.poll())
                if rep_socket in messages:
                    message = rep_socket.recv()
                    print("REP: " + message)
                if sub_socket in messages:
                    message = sub_socket.recv()
                    print("SUB: " + message)
        except Exception as e: # TODO:buscar nombre de la interrupción
            print(e)
        except KeyboardInterrupt as e:
            #print(e)
            self.p.join(0.2)

    def publish_thread(self):
        while True:
            if self.publish_queue:
                socket = self.context.socket(zmq.PUB)
                socket.bind(CONNECT_FORMAT_STR.format(
                    protocol=PROTOCOL,
                    address="*",
                    port=str(int(self.port)+2)
                ))
                while self.publish_queue:
                    message = self.publish_queue.pop()
                    print(message)
                    socket.send(to_bytes(message))
                socket.close()

    def show_messages(self):
        print(self.message_queue)

    def broadcast_message(self, broadcast_address):
        print(":)")

    def __del__(self):
        self.p.join()

    def update_message_queue(self, message):
        self.message_queue.append(message)

def to_bytes(message: str) -> bytes:
    if isinstance(message, bytes):
        return message
    else:
        return str(message).encode("utf-8").strip()
