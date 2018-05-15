"""
Aquí está la configuración del servidor que corre Flask y conecta,
usando socket.io, con el cliente para hacer una página web actualizable
en tiempo real.

.. todo::

    - Orientarlo a objetos, tal vez
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

from multiprocessing import Process
from threading import Thread
from pprint import pformat

from flask import (Flask, render_template, copy_current_request_context,
    request, jsonify)
from flask_socketio import SocketIO, emit

import zmq

from crypto import encrypt_for_vote, load_keys
    
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
    logger.debug("Peer list " + repr(peer_list))
except Exception as e:
    logger.warning(e)
    peer_list = []
    logger.debug("No previous peers detected, creating new file at " + PEER_LIST_FILE)

app = Flask(__name__)
app.config.DEBUG = True
#app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode="eventlet") 

@app.route("/")
def index():
    return render_template("index.html")


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
    print(pformat(request.args))
    try:
        election_id = request.args.get("election_id", 0, type=int)
        option_id = request.args.get("option_id", 0xFF, type=int)
        signature = request.args.get("signature", 0, type=int)
        options = [0, 0, 0, 0, 0]
        options[option_id] = 1
        #: XXX: Inicio bloque de transmisión
        response = {}
        response = dict(
            election_id=election_id,
            options=encrypt_for_vote(load_keys("key")[0], options),
            signature=signature
        )
       # response["election_id"] = election_id
        #response["options"] = encrypt_for_vote(load_keys("key")[0], options)
        #response["signature"] = signature

        #: XXX: Fin bloque de transmisión
        return jsonify(**response)
    except Exception as e:
        print(e)
        return jsonify({})

@app.route("/create", methods=("POST",))
def create_election():
    return jsonify({})


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
                    print(e)

        socketio.start_background_task(target=f)
        thread = True


@socketio.on("message")
def log_message(message):
    logger.info("Message received: \"" + message + "\"")

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=8000, debug=True) 
