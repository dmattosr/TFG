"""
.. todo::
    - Quitar el hardcoding de la dirección del servidor de descubrimiento
    - Eliminar la excepción de interrupción del hilo de mensajes

En este fichero se encuentra el nodo comunicativo de la blockchain.
Estos nodos componen la red P2P, siendo efectivamente los *peers* de
esta.

"""

import json
import logging

from multiprocessing import Process
from threading import Thread
from pprint import pformat
from random import randint
from time import sleep, time
from uuid import uuid4

import zmq

from blockchain import Blockchain
from crypto import construct_proof, encrypt_for_vote, load_keys

CONNECT_FORMAT_STR = "{protocol}://{address}:{port}"
PROTOCOL = "tcp"

LOGGER_NAME = "node " + str(hash(time()))
LOGGER_FORMAT = "[%(levelname)s][%(asctime)s][%(name)s] %(message)s"
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format=LOGGER_FORMAT)

HEARTBEAT_INTERVAL = 5

class Node:
    """
    La clase nodo
    """

    def __init__(self, port):
        self.uuid = "-".join([str(field) for field in uuid4().fields])
        self.context = zmq.Context()
        self.port = str(port)
        self.running = True
        self.p = Thread(target=self._handle_messages)
        self.p.start()
        self.publish_queue = []
        self.t = Thread(target=self._publish_thread)
        self.t.start()
        self.peers = []
        self.chain_ring = {0: {"public_key": load_keys("key")[0]}}

    def load_peers(self, path):
        path = "conf/peers.json"
        try:
            self.peers.extend(json.load(open(path)))
            logger.debug("Loaded peer list succesfully from " + path)
            logger.debug("Peer list " + repr(self.peers))
        except Exception as e:
            logger.warning(e)
            logger.debug("No previous peers detected, creating new file at " + path)

    def save_peers(self, path):
        with open(path, "w+") as f:
            json.dump(self.peers, f)

    def serialize(self) -> dict:
        """
        Devuelve un diccionario de Python con la información apta para
        ser serializada a algún formato (principalmente JSON).
        """
        return {
            #"uuid": self.uuid,
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
        socket.close()

    def send_info(self, address: str, port: int, **kwargs):
        """
        Envía información sobre sí mismo por la red
        """
        logger.info(json.dumps(self.serialize()).encode())
        self.send_message(b"PEER " + json.dumps(self.serialize()).encode(), address, port)

    def send_vote(self, election_id, options, signature: int):
        """
        .. todo::
            Considerar cambiar la entrada por parámetros con nombre
            por un dict

        Construye un mensaje de votación y lo envía a la cola de
        publicación.

        :param election_id: El id de la elección.
        :type election_id: int
        :param option_id: Un array del voto encriptado.
        :param proofs: Las ZKP no interactivas que validan el voto.
        :param signature: La firma que certifica la pertenencia del
            votante a la elección.

        :returns: El ticket de auditoría criptográfica

        :raises ValueError: cuando alguno de los parámetros no está
            en un formato adecuado
        """
        #:TODO: Verificadores de validez de entradas
        
        public_key = self.chain_ring[election_id]["public_key"]
        encrypted_options = encrypt_for_vote(options, public_key)

        vote = {
            "election_id": election_id,
            "options": encrypted_options,
            "proofs": construct_proof(encrypted_options, public_key),
            "signature": signature
        }
    
        vote_message = "VOTE " + json.dumps(vote)

        self.publish_queue.append(vote_message)
        self.send_message(vote_message.encode(), "127.0.0.1", 5560)
        #:TODO: make_receipt

        return vote

    def _handle_messages(self):
        """
        Este método maneja la llegada de mensajes al nodo mediante un
        sistema de polling. Corre en un hilo nuevo al ser creado el
        nodo.
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
        while self.running:
            try:
                messages = dict(poller.poll(1000))
                if rep_socket in messages:
                    message = rep_socket.recv()
                    logger.info("REP: " + str(message))
                    rep_socket.send(b"READY")
                if sub_socket in messages:
                    message = sub_socket.recv()
                    logger.info(f"SUB: " + str(message))
                    if message[0:4] == b"PEER":
                        peer_info = json.loads(message.decode()[4:])
                        if peer_info not in self.peers and self.serialize() != peer_info:
                            #: TODO: Hacer verificación
                            try:
                                self.peers.append(peer_info)
                            except ValueError as e:
                                pass
            except Exception as e:
                self.running = False
                self.p.join()
                self.t.join()

    def _publish_thread(self):
        """
        Revisa periódicamente la cola de publicaciones pendientes y las
        publica a 
        .. todo::
            Revisar que no se repitan puertos dentro de los peers
        """
        while self.running:
            if self.publish_queue:
                socket = self.context.socket(zmq.DEALER)
                while self.publish_queue:
                    message = self.publish_queue.pop()
                    for peer in self.peers:
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
        self.running = False
        self.t.join()
        self.p.join()

    def add_peer(peer_info: dict):
        #XXX: sanitizar y verificar
        self.peers.append(peer_info)


def sanitize_info(info: dict):
    sanitized_info = {}

    # TODO: Verificar si los datos son de tipo correcto
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
