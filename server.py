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

import hashlib
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

import eventlet.green.zmq as zmq

from crypto import (encrypt_for_vote, load_keys,
        reconstruct_key, load_decryption_table, update_decryption_table, save_decryption_table)
from blockchain import Blockchain
from utils import get_final_votes

publish_queue = []

LOGGER_NAME = "Flask server"
LOGGER_FORMAT = "[%(levelname)s][%(asctime)s][%(name)s] %(message)s"
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logging.basicConfig(format=LOGGER_FORMAT)

thread = None

DECRYPT_TABLE_FILE = "conf/decrypt_table"
decrypt_table = load_decryption_table({}, DECRYPT_TABLE_FILE)

PEER_LIST_FILE = "conf/peers.json"
try:
    peer_list = json.load(open(PEER_LIST_FILE))
    logger.debug("Loaded peer list succesfully from " + PEER_LIST_FILE)
    logger.debug("Peer list " + repr(peer_list)) #XXX#
except Exception as e:
    logger.warning(e)
    peer_list = []
    logger.debug("No previous peers detected, creating new file at " + PEER_LIST_FILE)

def load_blockchain(path_file):
    try:
        loaded_chain = json.load(open(path_file))
        ring = {}
        for i in list(loaded_chain.keys()):
            # XXX: Resulta que json solo admite strings como keys, entonces
            # hay que convertir la clave a int
            key = int(i)
            ring[key] = Blockchain.construct(json.loads(loaded_chain[i]))
        logger.debug("Loaded chain ring succesfully from " + path_file)
        logger.debug("Chain ring: " + repr(list(ring.keys())))
        return ring
    except Exception as e:
        logger.warning(e)
        logger.debug("No chains detected, creating new file at " + path_file)
        return {}

CHAIN_RING_FILE = "conf/chain.json"
FINISHED_CHAIN_RING_FILE = "conf/fchain.json"
chain_ring = load_blockchain(CHAIN_RING_FILE) 
finished_chain_ring = load_blockchain(FINISHED_CHAIN_RING_FILE)

def save_chain_ring(ring, filepath):
    with open(filepath, "w") as f:
        json.dump({chain_id: ring[chain_id].serialize() for chain_id in ring}, f)


app = Flask(__name__)
app.config.DEBUG = True
#app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode="eventlet") 

def update_chains():
    finished_chains = list(filter(lambda c: chain_ring[c].end_time < time.time(), chain_ring))
    finished_chain_ring.update({c: chain_ring.pop(c) for c in finished_chains})
    if list(finished_chains):
        logger.info("LAS ELECCIONES {} HAN ACABADO".format(", ".join([str(c) for c in finished_chains])))
    save_chain_ring(chain_ring, CHAIN_RING_FILE)
    save_chain_ring(finished_chain_ring, FINISHED_CHAIN_RING_FILE)
    save_decryption_table(decrypt_table, DECRYPT_TABLE_FILE)

update_chains()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/tally")
def tally():
    return render_template("tally.html", elections=get_ids_for_template(finished_chain_ring), title="ELECCIONES FINALIZADAS")

@app.route("/tally/<int:election_id>")
def tally_final(election_id):
    election_chain = finished_chain_ring[election_id]
    return render_template("tally_final.html",
            election=election_chain.name,
            tally = list(zip(election_chain.options, get_final_votes(election_chain)))
            )

@app.route("/create")
def create():
    return render_template("index.html")

@app.route("/monitor")
def monitor():
    return render_template("monitor.html")

@app.route("/elections")
def elections():
    return render_template("elections.html", elections=get_ids_for_template(chain_ring), title="ELECCIONES EN CURSO")

from utils import create_new_key_dict

@app.route('/elections/<int:election>')
def vote(election):
    election_chain = chain_ring[election]
    sig = hashlib.sha256(request.remote_addr.encode()+request.user_agent.string.encode()).hexdigest()
    sig_exists = False
    if sig in create_new_key_dict(election_chain.votes, "signature"):
        sig_exists = True
    return render_template(
        "options.html",
        election=election_chain.name,
        checksum=zlib.crc32(str(election).encode()),
        options=election_chain.options,
        election_id=election,
        signature=sig,
        signature_already_exists=sig_exists
    )

@app.route("/cast", methods=("POST",))
def cast():
    logger.debug("REQUEST FORM: " + repr(request.form))
    
    option = int(request.form.get("option"))
    election_id = int(request.form.get("election_id"))
    chain = chain_ring.get(election_id)
    options = [0 for _ in chain.options]
    options[option] = 1
    options, proofs = encrypt_for_vote(chain.public_key, options)
    vote_ticket = dict(
        options=options,
        proofs=proofs,
        signature=hashlib.sha256(request.remote_addr.encode()+request.user_agent.string.encode()).hexdigest()
    )
    print("\n\n", vote_ticket, "\n\n")
    chain.create_vote(**vote_ticket)
    #broadcast_vote(**vote_ticket)
    update_chains()
    vote_ticket["election_id"] = election_id
    return render_template("cast.html", vote_ticket=json.dumps(vote_ticket)) 

def broadcast_vote(options, proofs, signature):
    socket = zmq.Context().socket(zmq.DEALER)
    for peer in peer_list:
        socket.connect("tcp://{}:{}".format(peer["ip_address"], peer["rep_port"]))
        socket.send(b"", zmq.SNDMORE)
        socket.send(b"VOTE " + json.dumps({
            "options": options,
            "proofs": proofs,
            "signature": signature,
        }).encode())
    socket.close()

               

def get_ids_for_template(ring):
    names = []
    election_ids = []
    crc_ids = []
    for election_id in ring:
        election_ids.append(election_id)
        crc_ids.append(zlib.crc32(str(election_id).encode()))
        names.append(ring.get(election_id).name)
    
    return zip(election_ids, crc_ids, names)

@app.route("/api/send", methods=("POST",))
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
        vote_ticket = dict(
            options=encrypt_for_vote(chain.get_public_key(), options),
            proofs=construct_proof(options, chain.get_public_key()),
            signature=signature
        )
        chain.create_vote(**vote_ticket)
        save_chain_ring(chain_ring, CHAIN_RING_FILE)
        vote_ticket["election_id"] = election_id
        #: XXX: Fin bloque de transmisión
        return jsonify(**vote_ticket)
    except Exception as e:
        logger.warning(e)
        return jsonify({})

@app.route("/api/create", methods=("POST",))
def create_election():
    election_data = request.get_json()
    logger.debug(election_data)
    name = election_data.get("name")
    election_id = SystemRandom().randint(0, 2**256-1)
    while election_id in chain_ring:
        election_id = SystemRandom().randint(0, 2**256-1)
    start_time = float(election_data.get("start_time", time.time()))
    end_time = float(election_data.get("end_time", time.time() + 3600))
    public_key = election_data.get("public_key")
    voter_list = election_data.get("voter_list")
    option_list = election_data.get("option_list")
    
    chain_ring[election_id] = Blockchain(start_time, None, end_time, reconstruct_key(public_key), voter_list, option_list, name)
    save_chain_ring(chain_ring, CHAIN_RING_FILE)
    eventlet.spawn_n(update_decryption_table, decrypt_table, chain_ring[election_id].public_key)
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


def run_proof_of_work():
    logger.debug("STARTED BACKGROUND TASK: PROOF OF WORK")
    while True:
        for chain in chain_ring.values():
            idx = chain.create_new_block(chain.proof_of_work()).get("index")
            if idx:
                logger.debug("BLOQUE (N {}) CREADO EN ELECCIÓN {}".format(
                    idx, chain.name))
        update_chains()
        eventlet.sleep(3)

socketio.start_background_task(target=run_proof_of_work)

@socketio.on("message")
def log_message(message):
    logger.info("Message received: \"" + message + "\"")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000, debug=True) 
