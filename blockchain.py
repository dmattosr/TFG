"""
Aquí se encuentra la definición de las clases necesarias para el uso de
la blockchain.
"""

import hashlib
import json
import os
import time
from random import SystemRandom

import crypto


GENESIS_BLOCK_TEMPLATE = {
    "start_timestamp": None,
    "end_timestamp" : None,
    "public_key": None,
    "voters": [],
    "options": []
}

def sha256hash(string):
    return hashlib.sha256(string.encode()).hexdigest()

def proof_is_valid(prev_proof, prev_hash, proof): #XXX
    """
    """
    guess = sha256hash(f"{prev_proof}{prev_hash}{proof}")
    return guess[:5] == "00000"

class Blockchain:

    def __init__(self, start_time, end_time, public_key, voter_list, option_list, name="votacion"):
        """
        .. todo::
            El timestamp debería estar firmado digitalmente por alguna
            autoridad
        """
        genesis_block = {
            "index": 0,
            "proof": SystemRandom().randint(0, 2**128),
            "start_time": start_time if start_time else time.time(),
            "end_time": end_time,
            "public_key": public_key,
            "voter_list": voter_list,
            "option_list": option_list,
            "name": name
        }
        self.blocks = [genesis_block]
        self.pending_transactions = []

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

    def serialize(self):
        serializable_genesis_block = self.blocks[0].copy()
        serializable_genesis_block["public_key"] = crypto.serialize_key(serializable_genesis_block["public_key"])
        return json.dumps([serializable_genesis_block] + self.blocks[1:])
        
    def create_new_block(self):
        if not self.pending_transactions:
            return {}
        new_block = {
            "index": len(self.blocks),
            "timestamp": time.time(),
            "proof": self.proof_of_work(),
            "previous_hash": self.hash(self.blocks[-1]),
            "transactions": self.pending_transactions
        }
        self.pending_transactions = []
        self.blocks.append(new_block)

        return self.blocks[-1]

    def create_vote(self, options, proofs, signature):
        self.pending_transactions.append({
            "options": options,
            "proofs":  proofs,
            "signature": signature
        })

       	return self.blocks[-1]["index"] + 1
   
    @staticmethod
    def hash(block):
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

    def __repr__(self):
        return self.serialize()

    def __str__(self):
        return self.serialize()


# verificar voto
# verificar que tenga la misma cantidad de las opciones
