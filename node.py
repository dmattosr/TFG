"""
.. todo::
    - Quitar el hardcoding de la dirección del servidor de descubrimiento
    - Eliminar la excepción de interrupción del hilo de mensajes

En este fichero se encuentra el nodo comunicativo de la blockchain.
Estos nodos componen la red P2P, siendo efectivamente los *peers* de
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
    """
    La clase nodo
    """

    def __init__(self, port):
        self.uuid = "-".join([str(field) for field in uuid4().fields])
        self.context = zmq.Context()
        #: Elige un puerto efímero aleatorio
        # self.port = randint(49152, 65535)
        self.port = str(port)
        #self.p = Process(target=self.handle_messages, args=(self.message_queue,))
        self.p = Thread(target=self.handle_messages)
        self.p.start()
        self.publish_queue = []
        self.t = Thread(target=self.publish_thread)
        self.t.start()
        self.peers = []

    def deserialize(self) -> dict:
        """
        Devuelve un diccionario de Python con la información apta para
        ser deserializada a algún formato (principalmente JSON).
        """
        return {
            "uuid": self.uuid,
            "port": self.port,
            "info": self.connection_information(),
        }

    def send_message(self, message: bytes, address: str, port: int):
        """
        Envía un mensaje en estilo de comunicación *non-blocking*
        mediante un socket de tipo *dealer* de ZeroMQ.

        :parámetros:
            - :message (:var bytes:): El mensaje a transmitir
        """
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

    def connection_information(self) -> dict:
        return {
            "ip_address": "127.0.0.1", # TODO: Cambiar
            "rep_port": self.port,
            "sub_port": str(int(self.port) + 1),
        }

    def send_info(self, address: str, port: int):
        """
        Envía información sobre sí mismo por la red
        """
        #self.send_message(json.dumps(self.connection_information()).encode(), address, port)
        self.send_message(b"PEER " + json.dumps(self.deserialize()).encode(), address, port)

    def handle_messages(self):
        rep_socket = self.context.socket(zmq.REP)
        rep_socket.bind(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address="*",
            port=self.port
        ))
        sub_socket = self.context.socket(zmq.SUB)
        """sub_socket.bind(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address="*",
            port=str(int(self.port) + 1)
        ))"""
        sub_socket.connect(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address="127.0.0.1",
            port="5561"
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
                    print("REP: " + str(message))
                    rep_socket.send(b"READY")
                    self.update_message_queue(message)
                if sub_socket in messages:
                    message = sub_socket.recv()
                    print(f"SUB: " + str(message))
                    if message[0:4] == b"PEER":
                        peer = json.loads(message[4:])
                        if peer["uuid"] != self.uuid:
                            self.peers.append(peer)
        except Exception as e: # TODO:buscar nombre de la interrupción
            print(e)
        except KeyboardInterrupt as e:
            #print(e)
            self.p.join(0.2)

    def publish_thread(self):
        while True:
            if self.publish_queue:
                socket = self.context.socket(zmq.PUB)
                while self.publish_queue:
                    message = self.publish_queue.pop()
                    for peer in self.peers:
                        socket.connect(CONNECT_FORMAT_STR.format(
                            protocol=PROTOCOL,
                            address=peer["info"]["ip_address"],
                            port=5561#peer["info"]["sub_port"]
                        ))
                        socket.send(to_bytes(message))
                socket.close()
            sleep(0.5)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return pformat(self.deserialize(), indent=1, width=80)

    def __del__(self):
        self.p.join()


def to_bytes(message: str) -> bytes:
    if isinstance(message, bytes):
        return message
    else:
        return str(message).encode("utf-8").strip()
