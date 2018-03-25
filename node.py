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

    def receive_message(self, address="*"):
        socket = self.context.socket(zmq.REP)
        #socket.connect("tcp://127.0.0.1:5555")# + str(self.port))
        # buscar qué significa el asterisco de recibir porque no tengo
        # idea, supongo que es «aceptar de cualquier dirección»
        # socket.bind("tcp://*:" + str(self.port))
        socket.bind(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address=address,
            port=self.port
        ))
        try:
            message = socket.recv()
            self.message_queue.append(message)
        except: # TODO:buscar nombre de la interrupción
            pass
        finally:
            socket.close()
            sleep(1)
        #return message

    def handle_messages(self):
        socket = self.context.socket(zmq.REP)
        socket.bind(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address="*",
            port=self.port
        ))
        while True:
            try:
                message = socket.recv()
                socket.send(b"READY")
                self.update_message_queue(message)
            except Exception as e: # TODO:buscar nombre de la interrupción
                print(e)
                break
            except KeyboardInterrupt as e:
                print(e)
                break
            #finally:
            #    sleep(1)

    def show_messages(self):
        print(self.message_queue)

    def broadcast_message(self, broadcast_address):
        print(":)")

    def __del__(self):
        self.p.terminate()

    def update_message_queue(self, message):
        self.message_queue.append(message)
