"""
Aquí se encuentra la definición de las clases necesarias para el uso de
la blockchain.
"""

import json
import os
import time
from random import SystemRandom
from functools import reduce
from pprint import pformat, saferepr

import crypto
from crypto import sha256hash

DIFFICULTY = 3

GENESIS_BLOCK_TEMPLATE = {
    "start_timestamp": None,
    "end_timestamp" : None,
    "public_key": None,
    "voters": [],
    "options": []
}

def proof_is_valid(prev_proof, prev_hash, proof): #XXX
    """
    Devuelve si la cadena resultante de aplicar una función hash sobre un conjunto de cadenas concatenadas es igual a un número de ceros concreto.

    :return: Si las cadenas concatenadas sirven como *proof-of-work*.
    """
    guess = sha256hash(f"{prev_proof}{prev_hash}{proof}")
    return guess[:DIFFICULTY] == "0" * DIFFICULTY

class Blockchain:

    def __init__(self, start_time, timestamp, end_time, public_key, voter_list, option_list, name="votacion"):
        """
        .. todo::
            El timestamp debería estar firmado digitalmente por alguna
            autoridad
        """
        genesis_block = {
            "index": 0,
            "proof": SystemRandom().randint(0, 2**128),
            "start_time": start_time if start_time else time.time(),
            "timestamp": timestamp if timestamp else time.time(),
            "end_time": end_time,
            "public_key": public_key,
            "voter_list": voter_list,
            "option_list": option_list,
            "name": name
        }
        self.blocks = [genesis_block]
        self.pending_votes = []

    @staticmethod
    def construct(blocks):
        blocks[0].pop("index")
        blocks[0].pop("proof")
        key = crypto.reconstruct_key(blocks[0].pop("public_key"))
        blocks[0]["public_key"] = key
        genesis = blocks[0]
        ret = Blockchain(**genesis)
        ret.blocks.extend(blocks[1:])
        return ret

    def load(filename):
        try:
            if os.path.isfile(filename):
                with open(filename, "r") as infile: 
                    blocks = json.load(infile)
                    loaded_blockchain = Blockchain(**blocks[0])
                    loaded_blockchain.blocks = blocks
                    return loaded_blockchain
        except Exception as e:
            print(e)
            return None

    def save(self, filename):
        try:
            with open(filename, "w") as outfile:
                json.dump(self.blocks, outfile)
        except Exception as e:
            print(e)

    def serialize_genesis_block(self):
        serializable_genesis_block = self.blocks[0].copy()
        serializable_genesis_block["public_key"] = crypto.serialize_key(serializable_genesis_block["public_key"])
        return serializable_genesis_block


    def serialize(self):
        return json.dumps([self.serialize_genesis_block()] + self.blocks[1:])

    def pretty_serialize(self):
        return saferepr([self.serialize_genesis_block()] + self.blocks[1:])
        
    def create_new_block(self, proof):
        if not self.pending_votes:
            return {}
        new_block = {
            "index": len(self.blocks),
            "timestamp": time.time(),
            "proof": proof,
            "previous_hash": self.hash(self.blocks[-1]),
            "transactions": self.pending_votes
        }
        self.pending_votes = []
        self.blocks.append(new_block)

        return self.blocks[-1]

    def create_vote(self, options, proofs, signature):
        self.pending_votes.append({
            "options": options,
            "proofs":  proofs,
            "signature": signature
        })

       	return self.blocks[-1]["index"] + 1
   
    def hash(self, block):
        if block == self.blocks[0]:
            return sha256hash(json.dumps(self.serialize_genesis_block()))
        block_info = json.dumps(block, sort_keys=True)
        return sha256hash(block_info)

    def proof_of_work(self):
        """
        Implementación sencilla de *proof-of-work* (POW):

        - Se concatena un número con el número anterior tal que, al
        aplicarle una función hash, la cadena resultante empiece con
        4 ceros

        :return: <int>
        """

        prev_proof = self.blocks[-1]['proof']
        prev_hash = self.hash(self.blocks[-1])

        proof = SystemRandom().randint(0, 2**128)
        while not proof_is_valid(prev_proof, prev_hash, proof):
            proof += 1

        return proof

    def validate(self):
        """
        Comprueba la validez de la blockchain: verifica que los bloques
        tengan tiempos de creación ordenados en el tiempo y que las
        pruebas sean siempre válidas.
        
        :returns: `True` si la cadena válida, un `False` en cualquier
            otro caso.
        """
        last_time = self.blocks[0]
        for block_i in range(1, len(self.blocks)-1):
            #: Verificamos que el pow es válido
            prev_block = self.blocks[block_i-1]
            block = self.blocks[block_i]
            if not proof_is_valid(prev_block["proof"], self.hash(prev_block), block["proof"]):
                print("AAAA")
                return False
            if block["timestamp"] < prev_block["timestamp"]:
                return False
        return True

    def update_chain(self, others):
        get_longest = lambda x, y: x if len(x) > len(y) else y
        self.blocks.extend(other[len(self.blocks):])

            


    def __repr__(self):
        return self.pretty_serialize()

    def __str__(self):
        return self.__repr__()

    def get_name(self):
        return self.blocks[0].get("name")

    def get_public_key(self):
        return self.blocks[0].get("public_key")

    def get_options(self):
        return self.blocks[0].get("option_list")

    def get_voters(self):
        return self.blocks[0].get("voter_list")

    def get_start_time(self):
        return self.blocks[0].get("start_time")

    def get_end_time(self):
        return self.blocks[0].get("end_time")

    def get_votes(self):
        votes = [b.get("transactions") for b in self.blocks[1:]]
        return reduce(lambda x, y: x+y, votes) if votes else []

    name = property(get_name)
    public_key = property(get_public_key)
    options = property(get_options)
    start_time = property(get_start_time)
    end_time = property(get_end_time)
    voters = property(get_voters)
    votes = property(get_votes)

# verificar voto
# verificar que tenga la misma cantidad de las opciones
