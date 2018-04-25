"""
Aquí está la configuración del servidor que corre Flask y conecta,
usando socket.io, con el cliente para hacer una página web actualizable
en tiempo real.

.. todo:: Orientarlo a objetos, tal vez
"""

#: eventlet debe ser importado primero
import eventlet
#: La función monkey_patch modifica clases de la librería estándar, por
#: tanto se tiene que ejecutar antes de importar alguna otra cosa.
eventlet.monkey_patch()

import json
import logging

from multiprocessing import Process
from threading import Thread
from pprint import pformat

from flask import (Flask, render_template, copy_current_request_context,
    request, jsonify)
from flask_socketio import SocketIO, emit

import zmq

thread = None

LOGGER_NAME = "Flask server"
LOGGER_FORMAT = "[%(levelname)s][%(asctime)s][%(name)s] %(message)s"
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format=LOGGER_FORMAT)

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
    election_id = request.args.get("election_id", "0", type=str)
    option_id = request.args.get("option_id", "0", type=str)
    #: XXX: Inicio bloque de transmisión
    response = {}
    response["election_id"] = election_id
    response["option_id"] = option_id
    #: XXX: Fin bloque de transmisión
    return jsonify(**response)

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
                        logger.debug("message as json: " + json.dumps(msg[5:].decode()))
                        socket.send(b"READY")
                        emit("json", json.loads(msg[5:].decode()), broadcast=True)
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
