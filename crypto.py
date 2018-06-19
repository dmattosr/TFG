"""
Aquí está el conjunto de funciones de criptografía relacionados a la
encripción ElGamal homomórfica y un conjunto de utilidades que permiten
trabajar con ella
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

"""
-------------------- Utilidades matemáticas --------------------
Las siguientes son funciones de uso matemático. Son algoritmos
usados por los protocolos criptográficos.
"""
def discrete_log(a, b, n):
    """
    Resuelve el problema del logaritmo discreto mediante el
    algoritmo *giant-step baby-step*.

    La definición teórica es: para un Grupo Ciclico G de orden n, con
    generador a y un elemento b, devuelve un número x satisfaciendo
    :math:`a^x=b`.

    Esta función está intencionada a ser usada en números pequeños,
    esto es: en el orden como máximo de los millones, como aquellos
    que resultan de las votaciones.

    :param a: El generador.
    :param b: El elemento para el cual se calcula el logaritmo
        discreto.
    :param n: El orden del grupo cíclico.

    :returns: El logaritmo discreto de b en el grupo cíclico G.
    """
    
    m = ceil(sqrt(n))
    trial = []
    for j in range(0, m):
        print("(", j, a**j, ")")
        trial.append((j, a**j))

    a_m = multiplicative_inverse(a**m, n)
    print("a_m: ", a_m)
    y = b
    for i in range(0, m):
        for first, second in trial:
            if second == y:
                return i * m + first
        y *= a_m
        print("y: ", y)
    return "-1"

def multiplicative_inverse(n, modulo):
    """
    Computa :math:`n^{-1} \\pmod{m}` usando el algoritmo de Gauss. Solo
    es válido si el modulo es primo .

    :param n: El número n.
    :param m: El módulo.
    :returns: El inverso multiplicativo de :math:`n \\pmod{m}`.
    :raises ValueError: Si el modulo no es primo.
    """
    if not is_prime(modulo):
        raise ValueError(
            "El módulo tiene que ser primo"
        )
    num = 1
    denum = n
    for i in range(modulo):
        x = ceil(modulo/denum)
        num = (x * num) % modulo 
        denum = (x * denum) % modulo
        if denum == 1:
            return num
    return -1

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
    Carga claves desde un fichero en formato JSON.

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
    que solo pueden ser 0 o 1.

    :param options: Una lista que representa el voto.
    :param key: La clave pública de la elección.

    :returns: Una lista que representa el voto encriptado.
    """
    for i in options:
        if i != 0 and i != 1:
            raise ValueError(
                "La papeleta {} está mal formada.".format(str(options))
            )
    
    #k_array = [generate_k(key.size()) for option in options]

    k = generate_k(127)#key.size())
    k_array = [k for i in range(len(options))]

    encrypted_ballot = [key.encrypt(pow(key.g, option), k) for option, k in zip(options, k_array)]
    proofs = construct_proof(key, options, encrypted_ballot, k_array)

    return encrypted_ballot, proofs

def generate_k(keysize):
	return Random.new().read(keysize)

def construct_proof(key, non_encrypted_ballot, encrypted_ballot, k_array):
    """
    Construye una prueba de cero conocimiento no interactiva con el
    protocolo Chaum-Pedersen disyuntivo (DCP).

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

            print(c0)
            print(r)

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

def verify_ballot(key, vote):
    valid_proofs = True
    for ballot, proof in zip(vote["options"], vote["proofs"]):
      proof_valid = verify_proof(key, ballot, proof)
      print(proof_valid)
      valid_proofs = valid_proofs and proof_valid
    print(valid_proofs)
    # Revisar firma
    print("\n")
    valid_signature = True

    return valid_proofs and valid_signature

def verify_proof(key, ballot, proof):
    a, b = ballot
    a0, a1, b0, b1, c0, c1, r0, r1 = proof
    g = key.g
    p = key.p
    pk = key.y

    s1 = pow(g, r0, p) == a0 * pow(a, c0, p) % p
    s2 = pow(g, r1, p) == a1 * pow(a, c1, p) % p
    s3 = pow(pk, r0, p) == b0 * pow(b, c0, p) % p
    s4 = pow(pk, r1, p) == b1 * pow(b * pow(g, p - 2, p) % p, c1, p) % p
    #print(s1, s2, s3, s4)
    # TODO: Hay un problema con cómo está descrito en el artículo, al 
    # parecer. La siguiente línea amerita revisión
    # s5 = (c0 + c1) % q == custom_hash([pk, a, b, a0, b0, a1, b1])
    return s1 and s2 and s3 and s4


def sha256hash(string):
    return hashlib.sha256(string.encode()).hexdigest()

def hash_proof(proof):
    return int(sha256hash("".join([str(i) for i in proof])), base=16)

def tally_votes(key, ballot_list):
    """
    Realiza la sumatoria de los votos en texto cifrado.
    
    :param key: La clave de la elección.
    :param ballot_list: La lista de papeletas cifradas.

    :returns: La sumatoria de votos.
    """
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
    Realiza el descifrado de los votos de manera directa.

    :param vote_tally: El escrutinio cifrado de votos.
    :param key: La clave para descifrar los votos.

    :returns: El escrutinio de votos descifrado.

    :raises ValueError: Si la clave no tiene el componente de clave
        privada.
    """
    if not key.has_private():
        raise ValueError
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
    raise NotImplementedError

#:TODO:Revisar esta documentación
def vote_lookup_table(key, n_votes):
    """
    Genera una *lookup table* para el logaritmo discreto a partir de
    una clave. La tabla resultante contiene en cada índice el valor del
    logaritmo discreto en el grupo cíclico para de la clave.

    :param key: La clave.
    :param n_votes: El número máximo de votos posibles para una misma
        opción. No es necesario calcular para más de esta cantidad.

    :returns: Una lista donde se encuentra cada logaritmo discreto
        posible en el dominio de la clave, donde el índice es la
        solución.
    """
    table = []
    for x in range(n_votes):
        table.append(pow(key.g, x, key.p))
    return table

def test_tally():
    #:TODO: Verificar que los votos tengan igual tamaño
    enc = []
    unenc = []
    a = [1, 0, 0, 0, 0, 0, 0]
    #key = generate_ElGamal_key(128)
    key = load_keys("key")[0]
    print("key generated")

    for i in range(1000):
        random.shuffle(a)
        unenc.append(a[:])

    for pp in range(100):
        unenc.append([0,1,0,0,0,0,0])

    print(unenc, "\n")

    for vote in unenc:
        enc.append(encrypt_for_vote(key, vote))

    print(enc, "\n")

    enc_tallied = tally_votes(key, enc)
    import json
    with open("shares", "r") as f:
        tallied = decrypt_vote_tally_threshold(key, json.load(f), enc_tallied)
    print(tallied, "\n")

    table = vote_lookup_table(key, 10000)
    print(table, "\n")

    print([table.index(i) for i in tallied], "\n")

def serialize_key(key: ElGamal):
    """
    Devuelve un dict de Python con la información de una clave lista para serializar. Incluye los parámetros de dominio (p, g), la clave pública (y), y de tenerla, la clave privada.

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
