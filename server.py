"""
Un servidor en Flask que conecta,
usando socket.io, con el cliente para hacer una página web actualizable
en tiempo real.

.. todo::

    - Falta una función generalizada para sanear los mensajes de
      descubrimiento y de votación

"""

#: eventlet debe ser importado primero
import eventlet
#: La función monkey_patch modifica clases de la librería estándar, por
#: tanto se tiene que ejecutar antes de importar alguna otra cosa.
eventlet.monkey_patch()

import json
import logging
import os
import time
import zlib

from multiprocessing import Process
from threading import Thread
from pprint import pformat
from random import SystemRandom

from flask import (Flask, render_template, copy_current_request_context,
    request, jsonify)
from flask_socketio import SocketIO, emit

import zmq

from crypto import (construct_proof, encrypt_for_vote, load_keys,
        reconstruct_key)
from blockchain import Blockchain 

LOGGER_NAME = "Flask server"
LOGGER_FORMAT = "[%(levelname)s][%(asctime)s][%(name)s] %(message)s"
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format=LOGGER_FORMAT)

thread = None

PEER_LIST_FILE = "conf/peers.json"
try:
    peer_list = json.load(open(PEER_LIST_FILE))
    logger.debug("Loaded peer list succesfully from " + PEER_LIST_FILE)
    logger.debug("Peer list " + repr(peer_list)) #XXX#
except Exception as e:
    logger.warning(e)
    peer_list = []
    logger.debug("No previous peers detected, creating new file at " + PEER_LIST_FILE)

CHAIN_RING_FILE = "conf/chain.json"
chain_ring = {}
try:
    loaded_chain = json.load(open(CHAIN_RING_FILE))
    for i in list(loaded_chain.keys()):
        # XXX: Resulta que json solo admite strings como keys, entonces
        # hay que convertir la clave a int
        key = int(i)
        chain_ring[key] = Blockchain.construct(json.loads(loaded_chain[i]))
    logger.debug("Loaded chain ring succesfully from " + CHAIN_RING_FILE)
    logger.debug("Chain ring: " + repr(list(chain_ring.keys())))
except Exception as e:
    logger.warning(e)
    logger.debug("No chains detected, creating new file at " + CHAIN_RING_FILE)

app = Flask(__name__)
app.config.DEBUG = True
#app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode="eventlet") 

def save_chain_ring():
    with open(CHAIN_RING_FILE, "w") as f:
        json.dump({chain_id: chain_ring[chain_id].serialize() for chain_id in chain_ring}, f)

@app.route("/")
def index():
    return render_template("index.html", elections=get_ids_for_template())

def get_ids_for_template():
    names = []
    election_ids = []
    for election_id in chain_ring:
        election_ids.append(zlib.crc32(str(election_id).encode()))
        names.append(chain_ring.get(election_id).blocks[0].get("name"))
    
    return zip(names, election_ids)

@app.route("/send", methods=("GET", "POST"))
def send():
    """
    .. todo::
        Un montón de cosas:

            - Hay que verificar si el voto es correcto, pertenece a una
              votación en marcha, etc.
            - Hay que mandar el voto emitido a los nodos una vez se haga
              esta verificación.

    """
    logger.debug(pformat(request.args))
    try:
        election_id = int(request.args.get("election_id", 0, type=int))
        chain = chain_ring.get(election_id)
        if not chain:
            return jsonify({})
        option_id = int(request.args.get("option_id", 0xFF, type=int))
        signature = int(request.args.get("signature", 0, type=int))
        options = [0 for i in range(len(chain.blocks[0]["option_list"]))]
        options[option_id] = 1
        #: XXX: Inicio bloque de transmisión
        vote_ticket = {}
        logger.debug("CREANDO VOTO")
        vote_ticket = dict(
            options=encrypt_for_vote(chain.blocks[0]["public_key"], options),
            proofs=construct_proof(options, chain.blocks[0]["public_key"]),
            signature=signature
        )
        logger.debug("VOTO CREADO")
        chain.create_vote(**vote_ticket)
        logger.debug("AÑADIDO A LA CHAIN")
        save_chain_ring();
        logger.debug("CHAIN guardadad")
        vote_ticket["election_id"] = election_id
        #: XXX: Fin bloque de transmisión
        return jsonify(**vote_ticket)
    except Exception as e:
        logger.warning(e)
        return jsonify({})

@app.route("/create", methods=("POST",))
def create_election():
    election_data = request.get_json()
    logger.debug(election_data)
    name = election_data.get("name", "votacion")
    election_id = SystemRandom().randint(0, 2**256-1)
    while election_id in chain_ring:
        election_id = SystemRandom().randint(0, 2**256-1)
    start_time = float(election_data.get("start_time", time.time()))
    end_time = float(election_data.get("end_time", time.time() + 3600))
    public_key = election_data.get("public_key")
    voter_list = election_data.get("voter_list")
    option_list = election_data.get("option_list")
    
    chain_ring[election_id] = Blockchain(start_time, end_time, reconstruct_key(public_key), voter_list, option_list, name)
    save_chain_ring()
    return jsonify({election_id: chain_ring[election_id].serialize()})

@socketio.on("connect")
def on_connect():
    """
    Desde que se conecta un usuario se empieza un thread. Dicho hilo
    corre el nodo zeromq que maneja la comunicación hacia los nodos
    peer.
    """
    logger.debug("USER CONNECTED")
    global thread
    if not thread:
        @copy_current_request_context
        def f():
            logger.debug("Binding socket...")
            context = zmq.Context()

            socket = context.socket(zmq.REP)
            socket.bind("{}://{}:{}".format("tcp", "*", 5560))
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)

            pub_socket = context.socket(zmq.PUB)
            pub_socket.bind("{}://{}:{}".format("tcp", "*", 5561))

            logger.debug("socket is binded")
            while True:
                try:
                    messages = dict(poller.poll(1000))
                    if socket in messages:
                        msg = socket.recv()
                        logger.debug("Received message on REP socket " + msg.decode())
                        socket.send(b"READY")
                        msg_header = msg.decode()[:4]
                        msg_dict = json.loads(msg.decode()[5:])
                        # aquí iría un "switch" para cada posible header
                        # este es solo para el header PEER
                        if msg_header == "PEER" and msg_dict not in peer_list:
                            with open(PEER_LIST_FILE, "w+") as f:
                                peer_list.append(msg_dict)
                                json.dump(peer_list, f)
                        # XXX: Tendría ahora que haber uno para VOTE
                        # que es ya el otro importante
                        if msg_header == "VOTE":
                            pass
                        emit("json", msg_dict, broadcast=True)
                        pub_socket.send(msg)
                    else:
                        eventlet.sleep(2)
                except Exception as e:
                    logger.warning(e)

        socketio.start_background_task(target=f)
        thread = True


@socketio.on("message")
def log_message(message):
    logger.info("Message received: \"" + message + "\"")

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=8000, debug=True) 
