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
        #self.p = Process(target=self._handle_messages, args=(self.message_queue,))
        self.p = Thread(target=self._handle_messages)
        self.p.start()
        self.publish_queue = []
        self.t = Thread(target=self.publish_thread)
        self.t.start()
        self.peers = []

    def serialize(self) -> dict:
        """
        Devuelve un diccionario de Python con la información apta para
        ser serializada a algún formato (principalmente JSON).
        """
        return {
            "uuid": self.uuid,
            "ip_address": "127.0.0.1", # TODO: Cambiar a dinámico
            "rep_port": self.port,
            "sub_port": str(int(self.port) + 1),
        }

    def send_message(self, message: bytes, address: str, port: int):
        """
        Envía un mensaje en estilo de comunicación *non-blocking*
        mediante un socket de tipo *dealer* de ZeroMQ.

        :param message: El mensaje a transmitir
        """
        socket = self.context.socket(zmq.DEALER)
        socket.connect(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address=address,
            port=str(port)
        ))
        socket.send(b"", zmq.SNDMORE)
        socket.send(message)
        #socket.recv()
        socket.close()

    def send_info(self, address: str, port: int, **kwargs):
        """
        Envía información sobre sí mismo por la red
        """
        self.send_message(b"PEER " + json.dumps(self.serialize()).encode(), address, port)

    def _handle_messages(self):
        """
        Este método empieza a correr en un nuevo hilo al crear una
        instancia del nodo, 
        """
        rep_socket = self.context.socket(zmq.REP)
        rep_socket.bind(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address="*",
            port=self.port
        ))
        sub_socket = self.context.socket(zmq.SUB)
        sub_socket.connect(CONNECT_FORMAT_STR.format(
            protocol=PROTOCOL,
            address="127.0.0.1",
            port=5561
        ))
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        poller = zmq.Poller()
        poller.register(rep_socket, zmq.POLLIN)
        poller.register(sub_socket, zmq.POLLIN)
        try:
            while True:
                messages = dict(poller.poll())
                if rep_socket in messages:
                    message = rep_socket.recv()
                    print("REP: " + str(message))
                    rep_socket.send(b"READY")
                    self.message_queue.append(message)
                if sub_socket in messages:
                    message = sub_socket.recv()
                    print(f"SUB: " + str(message))
                    if message[0:4] == b"PEER":
                        peer_info = json.loads(message[4:])
                        if (peer_info["uuid"] != self.uuid
                            and peer_info["uuid"] not in [i["uuid"] for i in self.peers]):
                            #: TODO: Hacer verificación
                            try:
                                self.peers.append(sanitize_info(peer_info))
                            except ValueError as e:
                                pass

        except KeyboardInterrupt as e:
            # TODO: Buscar como mandar a detener un hilo desde si mismo
            self.p.join(0.2)

    def publish_thread(self):
        while True:
            if self.publish_queue:
                while self.publish_queue:
                    message = self.publish_queue.pop()
                    for peer in self.peers:
                        socket = self.context.socket(zmq.DEALER)
                        socket.connect(CONNECT_FORMAT_STR.format(
                            protocol=PROTOCOL,
                            address=peer["ip_address"],
                            port=peer["rep_port"]
                        ))
                        socket.send(b"", zmq.SNDMORE)
                        socket.send(to_bytes(message))
                socket.close()
            sleep(1)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return pformat(self.serialize(), indent=1, width=80)

    def __del__(self):
        self.p.join()


def sanitize_info(info: dict):
    sanitized_info = {}

    # Verificar si los datos son de tipo correcto
    sanitized_info["uuid"] = info.get("uuid")
    sanitized_info["ip_address"] = info.get("ip_address")
    sanitized_info["rep_port"] = info.get("rep_port")
    sanitized_info["sub_port"] = info.get("sub_port")

    if None in sanitized_info.values():
        raise ValueError("La información de nodo no es correcta")

    return sanitized_info

def to_bytes(message: str) -> bytes:
    if isinstance(message, bytes):
        return message
    else:
        return str(message).encode("utf-8").strip()
