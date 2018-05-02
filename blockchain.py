"""
Aquí se encuentra la definición de las clases necesarias para el uso de
la blockchain.
"""

import json
import os
import time

import crypto


GENESIS_BLOCK_TEMPLATE = {
    "start_timestamp": None,
    "end_timestamp" : None,
    "public_key": None,
    "voters": [],
    "options": []
}

class Blockchain:

    def __init__(self, start_time, end_time, public_key, voter_list, option_list):
        """
        .. todo::
            El timestamp debería estar firmado digitalmente por alguna
            autoridad
        """
        genesis_block = {
            "start_time": start_time if start_time else time.time(),
            "end_time": end_time,
            "public_key": public_key,
            "voter_list": voter_list,
            "option_list": option_list
        }
        self.blocks = [genesis_block]
        self.pending_transactions = []

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
        return json.dumps(self.blocks)
        
    def create_new_block(self):
        new_block = {
            "n": len(self.blocks),
            "proof": None, # Aquí va la prueba de hashcash o similar,
            "previous_hash": ,
            "transactions": self.pending_transactions
        }
        self.pending_transactions = []
        self.blocks.append(new_block)

    def create_vote(self, election_id, option, proofs, signature):
        self.pending_transactions.append({
            "election_id": election_id,
            "option": option,
            "proofs":  proofs,
            "signature": signature
        })
        
    def __repr__(self):
        return self.serialize()

    def __str__(self):
        return self.serialize()
