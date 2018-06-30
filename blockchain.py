"""
Aquí se encuentra la definición de las clases necesarias para el uso de
la blockchain.
"""

import json
import os
import time

from functools import reduce
from pprint import pformat, saferepr
from random import SystemRandom

from crypto import reconstruct_key, serialize_key, sha256hash


DIFFICULTY = 6
"""
La dificultad de generar un proof válido. Corresponde a la cantidad de
ceros que se busca tenga el resultado de la función hash sobre la
concatenación de las cadenas apropiadas.
"""

class Blockchain:
    """
    Esta clase implementa la blockchain junto con los mecanismos
    básicos para su funcionamiento: creación de transacciones (votos,
    en este caso), creación de bloques, verificación de validez y
    actualización.
    """

    def __init__(self, start_time, timestamp, end_time, public_key, voter_list, option_list, name="votacion"):
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
        """
        A partir de un conjunto de `dict`s, reconstruye la cadena que
        representan.

        Utilizado en desserialización.

        :param blocks: una lista de dicts que representen una
            *blockchain*.
        """
        blocks[0].pop("index")
        blocks[0].pop("proof")
        key = reconstruct_key(blocks[0].pop("public_key"))
        blocks[0]["public_key"] = key
        genesis = blocks[0]
        ret = Blockchain(**genesis)
        ret.blocks.extend(blocks[1:])
        return ret

    @staticmethod
    def load(filename):
        """
        Carga desde un fichero la configuración de una blockchain y
        devuelve el objeto resultante.

        :param filename: el fichero desde el que cargar la
            configuración.
        """
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
        """
        Guarda en un fichero la configuración de la *blockchain*.

        :param filename: El fichero donde guardar la configuración.
        """
        try:
            with open(filename, "w") as outfile:
                json.dump(self.blocks, outfile)
        except Exception as e:
            print(e)

    def serialize_genesis_block(self):
        """
        Devuelve una `dict` que representa el bloque génesis apto para
        ser serializado.

        Esta función es necesaria ya que se tiene que poner en un
        formato serializable la clave del bloque génesis para poder
        guardarlo en disco duro o producir un *hash* de este bloque.
        """
        serializable_genesis_block = self.blocks[0].copy()
        serializable_genesis_block["public_key"] = serialize_key(serializable_genesis_block["public_key"])
        return serializable_genesis_block

    def serialize(self):
        """
        Serializa en formato JSON en una forma compacta.

        :return: una cadena representando el contenido de la
            *blockchain* apta para ser guardada en disco duro.
        """
        return json.dumps([self.serialize_genesis_block()] + self.blocks[1:], sort_keys=True)

    def pretty_serialize(self):
        """
        Serializa en formato JSON, pero con un formato más agradable a
        la vista, con indentaciones y todos los espacios apropiados.

        :return: una cadena representando el contenido de la
            *blockchain* apta para ser guardada en disco duro (o ser
            mostrada por pantalla).
        """
        return pformat([self.serialize_genesis_block()] + self.blocks[1:])
        
    @staticmethod
    def valid_proof(prev_proof, prev_hash, proof):
        """
        Devuelve si la cadena resultante de aplicar una función hash
        sobre un conjunto de cadenas concatenadas es igual a un número
        de ceros determinado por la dificultad.

        :return: Si el argumento `proof` sirve como *proof-of-work*.
        """
        proof_hash = sha256hash(f"{prev_proof}{prev_hash}{proof}")
        return proof_hash[:DIFFICULTY] == "0" * DIFFICULTY

    def create_new_block(self, proof):
        """
        Crea un bloque nuevo en la blockchain.

        Solo se creara un bloque si la prueba nueva es válida y hay
        votos pendientes de guardar en un bloque.

        :param proof: una prueba valida respecto al último bloque en la
            cadena.

        :return: el bloque nuevo creado en caso de que se haya creado
            correctamente o un `dict` vacío en caso contrario.
        
        """
        if not self.pending_votes:
            return {}

        prev_proof = self.blocks[-1]["proof"]
        prev_hash = self.hash(self.blocks[-1])

        if not self.valid_proof(prev_proof, prev_hash, proof):
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
        """
        Añade un voto a la lista de votos pendientes a ser añadidos a un
        bloque.

        :param options: el texto cifrado de la elección.
        :param proofs: las pruebas DCP.
        :param signature: la firma digital.

        :return: El índice del bloque en el que va a estar el voto
        """

        self.pending_votes.append({
            "options": options,
            "proofs":  proofs,
            "signature": signature
            })

       	return self.blocks[-1]["index"] + 1
   
    def hash(self, block):
        """
        Produce un *hash* SHA256 de los datos de un bloque.

        :param block: el bloque a pasar por la función *hash*.

        :return: el *hash* SHA256 de los datos del bloque.
        """
        if block == self.blocks[0]:
            return sha256hash(json.dumps(self.serialize_genesis_block()))
        block_info = json.dumps(block, sort_keys=True)
        return sha256hash(block_info)

    def proof_of_work(self):
        """
        Implementación sencilla de *proof-of-work* (POW): se concatena
        un número con el número anterior tal que, al aplicarle una
        función hash, la cadena resultante empiece con tantos ceros
        como defina la dificultad actual de la cadena.

        :return: Un *proof-of-work* apropiado para crear un bloque
            nuevo.
        """

        prev_proof = self.blocks[-1]["proof"]
        prev_hash = self.hash(self.blocks[-1])

        proof = SystemRandom().randint(0, 2**128)

        while not self.valid_proof(prev_proof, prev_hash, proof):
            proof += 1

        return proof

    def validate(self):
        """
        Comprueba la validez de la blockchain: verifica que los bloques
        tengan tiempos de creación ordenados en el tiempo y que todas
        las pruebas para sus bloques sean válidas.
        
        :returns: `True` si la cadena válida, un `False` en cualquier
            otro caso.
        """
        last_time = self.blocks[0]
        for block_i in range(1, len(self.blocks)-1):
            #: Verificamos que el pow es válido
            prev_block = self.blocks[block_i-1]
            block = self.blocks[block_i]
            if not self.valid_proof(prev_block["proof"], self.hash(prev_block), block["proof"]):
                return False
            if block["timestamp"] < prev_block["timestamp"]:
                return False
        return True

    def update_chain(self, chains):
        """
        Actualiza la cadena con la cádena válida más larga a partir de
        una lista.

        :param chains: Una lista de otras versiones de la misma blockchain
        """
        get_longest = lambda x, y: x if len(x) > len(y) else y

        valid_chains = filter(Blockchain.validate, chains)

        longest_chain = reduce(get_longest, valid_chains)

        if len(longest_chain.blocks) > self.blocks:
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
