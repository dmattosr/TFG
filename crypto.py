"""
Aquí está el conjunto de funciones de criptografía relacionados a el
cifrado ElGamal y un conjunto de utilidades que permiten trabajar con
él.
"""

import hashlib
import json

from math import ceil, floor, log, sqrt
from random import SystemRandom
from time import sleep

from gmpy2 import is_prime

from Crypto.PublicKey import ElGamal
from Crypto import Random
from Crypto.Random import random

from shamir import make_shares, recover_secret
from signature import is_valid_signature

"""
-------------------- Utilidades matemáticas --------------------
Las siguientes son funciones de uso matemático. Son algoritmos
usados por los protocolos criptográficos.
"""

def save_key(key, filepath):
    """
    Guarda una clave ElGamal a un fichero en formato JSON.

    :param key: La clave a ser guardada.
    :param filepath: <str> El fichero para guardar la clave.

    """
    key_dict = serialize_key(key)
    with open(filepath, "a+") as f:
        json.dump(key_dict, f)
        f.write("\n")

def load_keys(filepath):
    """
    Carga claves ElGamal desde un fichero en formato JSON.

    :param filepath: La dirección del fichero que contiene las claves.

    :returns: Una lista con las claves.
    """
    keys = []
    with open(filepath) as f:
        for line in f.readlines():
            k_dict = json.loads(line)
            keys.append(reconstruct_key(k_dict))
    return keys

def reconstruct_key(k_dict):
    """
    Reconstruye una clave a partir de un diccionario de Python.
    Utilizado para desserialización.

    :param k_dict: Un diccionario que describe una clave.

    :return: Un objeto de clave ElGamal.
    """
    p = k_dict.get("p")
    g = k_dict.get("g")
    y = k_dict.get("y")
    x = k_dict.get("x")
    if x:
        return ElGamal.construct((p, g, y, x))
    else:
        return ElGamal.construct((p, g, y))

def generate_ElGamal_key(keysize):
    """
    Genera una clave ElGamal del tamaño especificado.

    :param keysize: El tamaño de la clave.

    :returns: Una clave ElGamal.
    """
    return ElGamal.generate(keysize, Random.new().read)

def encrypt_for_vote(key, options):
    """
    Cifra una papeleta de votos, en el formato de un array de ints
    que solo pueden ser 0 o 1, y donde, como máximo, puede haber un 1.

    :param options: Una lista que representa el voto.
    :param key: La clave pública de la elección.

    :returns: Una lista que representa el voto cifrado.
    """
    for i in options:
        if i != 0 and i != 1:
            raise ValueError(
                "La papeleta {} está mal formada.".format(str(options))
            )
    
    #k_array = [generate_k(key.size()) for option in options]

    k = generate_k(127)#key.size())
    k_array = [k for i in range(len(options))]

    encrypted_ballot = [key.encrypt(pow(key.g, option, key.p), k) for option, k in zip(options, k_array)]
    proofs = construct_proof(key, options, encrypted_ballot, k_array)

    return encrypted_ballot, proofs

def generate_k(keysize):
    """
    Genera una clave efímera del tamaño en bits especificado.

    :param keysize: El tamaño de la clave en bits.
    :return: Un conjunto de bits apto para ser utilizado como clave
        efímera.
    """
    return Random.new().read(keysize)

def construct_proof(key, non_encrypted_ballot, encrypted_ballot, k_array):
    """
    Construye una prueba de cero conocimiento no interactiva con el
    protocolo Chaum-Pedersen disyuntivo (DCP).

    La descripción de este algoritmo se encuentra en 
    `<https://eprint.iacr.org/2016/765.pdf>`_.

    :param encrypted_ballot: La papeleta encriptada.
    :param key: La clave pública de la elección.

    :returns: Una lista con las pruebas criptográficas.
    """
    proofs = []
    pk = key.y
    g = key.g
    p = key.p
    q = (p - 1) // 2

    random = SystemRandom().randint

    for v, (a, b), r_bytes in zip(non_encrypted_ballot, encrypted_ballot, k_array):

        r = int(r_bytes.hex(), base=16)

        if v == 0:
            c1 = random(0, q - 1)
            r0 = random(0, q - 1)
            r1 = random(0, q - 1)

            a1 = pow(g, r1, p) * pow(a, c1 * (p - 2), p) % p
            b1 = pow(pk, r1, p) * pow(b * pow(g, p - 2, p) % p, c1 * (p - 2), p) % p

            a0 = pow(g, r0, p)
            b0 = pow(pk, r0, p)

            c = hash_proof([pk, a, b, a0, b0, a1, b1])
            c0 = (q + (c1 - c) % q) % q

            inter = c0 * r
            r0 = (r0 + (c0 * r) % q) % q

            proofs.append((a0, a1, b0, b1, c0, c1, r0, r1))

        elif v == 1:
            c0 = random(0, q - 1)
            r0 = random(0, q - 1)
            r1 = random(0, q - 1)

            a0 = pow(g, r0, p) * pow(a, c0 * (p - 2), p) % p
            b0 = pow(pk, r0, p) * pow(b, c0 * (p - 2), p) % p

            a1 = pow(g, r1, p)
            b1 = pow(pk, r1, p)

            c = hash_proof([pk, a, b, a0, b0, a1, b1])
            c1 = (q + (c0 - c) % q) % q

            r1 = (r1 + (c1 * r) % q) % q
            proofs.append((a0, a1, b0, b1, c0, c1, r0, r1))

    return proofs

def verify_ballot(key, vote, voter_list):
    """
    Verifica una papeleta, esto es: verifica que los textos cifrados
    de las opciones correspondan a 0 o a 1 exclusivamente y que la
    sumatoria de los valores de las opciones sea como máximo 1.

    :param key: La clave ElGamal.
    :param vote: La papeleta cifrada con las opciones en texto cifrado,
        las pruebas DCP y la firma.

    :return: Devuelve `True` si la papeleta es válida, `False` en
        cualquier otro caso.
    """
    valid_proofs = True

    for ballot, proof in zip(vote["options"], vote["proofs"]):
      proof_valid = verify_proof(key, ballot, proof)
      valid_proofs = valid_proofs and proof_valid

    valid_signature = valid_signature(vote["signature"], voter_list)

    return valid_proofs and valid_signature

def verify_proof(key, ciphertext, proof):
    """
    Verifica que una prueba DCP es válida para un texto cifrado ElGamal.

    .. warning:: El artículo de donde se ha sacado este algoritmo posee
        errores y no parece haber correciones disponibles. Se encuentra
        comentado por ello la última de las pruebas.

    :param key: La clave ElGamal.
    :param ciphertext: El texto cifrado.
    :param proof: La prueba en forma de lista

    :return: Devuelve `True` si la prueba es válida, `False` en
        cualquier otro caso.
    """
    a, b = ciphertext
    a0, a1, b0, b1, c0, c1, r0, r1 = proof
    g = key.g
    p = key.p
    pk = key.y

    s1 = pow(g, r0, p) == a0 * pow(a, c0, p) % p
    s2 = pow(g, r1, p) == a1 * pow(a, c1, p) % p
    s3 = pow(pk, r0, p) == b0 * pow(b, c0, p) % p
    s4 = pow(pk, r1, p) == b1 * pow(b * pow(g, p - 2, p) % p, c1, p) % p
    # TODO: Hay un problema con cómo está descrito en el artículo, al 
    # parecer. La siguiente línea amerita revisión
    # s5 = (c0 + c1) % q == custom_hash([pk, a, b, a0, b0, a1, b1])
    return s1 and s2 and s3 and s4


def sha256hash(string):
    """
    Función auxiliar que devuelve el *hash* SHA256 de una cadena en un
    formato cómodo de utilizar.

    :param string: la cadena a la que aplicar la función *hash*.
    
    :return: el hexadecimal correspondiente a la representación en
        bits del *hash* SHA256 de la cadena.
    """
    return hashlib.sha256(string.encode()).hexdigest()

def hash_proof(proof):
    """
    Una función hash utilizada en las pruebas de conocimiento cero
    para hacerla no interactiva.
    Concatena los elementos de la prueba y utiliza SHA256.
    
    :param proof: La prueba criptográfica, en forma de lista.
    :return: El hash de la prueba, en forma de número.
    """
    return int(sha256hash("".join([str(i) for i in proof])), base=16)

def tally_votes(key, ballot_list):
    """
    Realiza la sumatoria de los votos en texto cifrado.
    
    :param key: La clave de la elección.
    :param ballot_list: La lista de papeletas cifradas.

    :returns: La sumatoria de votos.
    """
    if not ballot_list:
        return []
    tallied = [[1,1] for i in range(len(ballot_list[0]))]
    for i in ballot_list:
        for c in range(len(i)):
            tallied[c][0] *= i[c][0]
            tallied[c][0] %= key.p
            tallied[c][1] *= i[c][1]
            tallied[c][1] %= key.p
    return [tuple(i) for i in tallied]


def decrypt_vote_tally(key, vote_tally):
    """
    Realiza el descifrado de los votos de manera directa cuando se
    tiene la clave privada.

    :param vote_tally: El escrutinio cifrado de votos.
    :param key: La clave para descifrar los votos.

    :returns: El escrutinio de votos descifrado.

    :raises ValueError: Si la clave no tiene el componente de clave
        privada.
    """
    if not key.has_private():
        raise ValueError("La clave para esta elección no tiene componente de clave privada")
    return list(map(lambda x: key.decrypt(x), vote_tally))


def decrypt_vote_tally_threshold(public_key, shares, vote_tally):
    """
    Realiza el descifrado de los votos mediante un esquema de cifrado
    umbral.

    .. note:: Idealmente no se reconstruye la clave sino que se usa
        algún protocolo de computación distribuida para ejectuar el
        cómputo **SIN** reconstruir la clave.

    :param public_key: La clave pública de la elección.
    :param vote_tally: El escrutinio cifrado de votos.
    :param shares: Una lista de secretos compartidos que permiten
        descifrar conjuntamente los votos.

    :returns: El escrutinio de votos descifrado.
    """
    private_key = ElGamal.construct((public_key.p, public_key.g, public_key.y, recover_secret(shares)))
    return list(map(lambda x: private_key.decrypt(x), vote_tally))


def vote_lookup_table(key, n_votes):
    """
    Genera una *lookup table* para el logaritmo discreto a partir de
    una clave. La tabla resultante contiene en cada índice el valor del
    logaritmo discreto para el número correspondiente en el grupo 
    cíclico de la clave.

    :param key: La clave.
    :param n_votes: El número máximo de votos posibles para una misma
        opción. No es necesario calcular para más de esta cantidad.

    :returns: Una lista donde se encuentra los valores de :math:`g^i mod p`
        para cada i desde 0 hasta el número de votantes. El valor del
        logaritmo discreto para un número x se consigue en el índice x.
    """
    return [pow(key.g, x, key.p) for x in range(n_votes)]


def serialize_key(key):
    """
    Devuelve un dict de Python con la información de una clave lista
    para serializar. Incluye los parámetros de dominio (p, g), la clave
    pública (y), y de tenerla, la clave privada.

    :param key: el objeto de clave a serializar

    :returns: un `dict` con la información de la clave.
    """
    if key.has_private():
        return {
            "p": key.p,
            "g": key.g,
            "y": key.y,
            "x": key.x,
        }
    else:
        return {
            "p": key.p,
            "g": key.g,
            "y": key.y,
        }

DECRYPTION_TABLE_DEFAULT = 100

def update_decryption_table(decryption_table, key, n_voters=DECRYPTION_TABLE_DEFAULT):
    if not key.has_private():
        return None
    if key.x not in decryption_table:
        decryption_table[key.y] = vote_lookup_table(key, n_voters)
    return decryption_table[key.y]


def save_decryption_table(decryption_table, filepath):
    try:
        with open(filepath, "w") as f:
            json.dump(decryption_table, f)
    except:
        pass


def load_decryption_table(decryption_table, filepath):
    try:
        with open(filepath, "r") as f:
            serialized = json.load(f)
        return {int(y): serialized[y] for y in serialized}
    except:
        return {}


def consult_decryption_table(decryption_table, key, n):
    return decryption_table.get(key.y).index(n)
