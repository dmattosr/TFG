"""
Aquí está el conjunto de funciones de criptografía relacionados a la
encripción ElGamal homomórfica y un conjunto de utilidades que permiten
trabajar con ella
"""

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
    with open("key", "a+") as f:
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
    Encripta una papeleta de votos, en el formato de un array de ints
    que solo pueden ser -1 o 1.

    :param options: Una lista que representa el voto.
    :param key: La clave pública de la elección.

    :returns: Una lista que representa el voto encriptado.
    """
    for i in options:
        if i != 0 and i != 1:
            raise ValueError(
                "La papeleta {} está mal formada.".format(str(options))
            )

    return [key.encrypt(pow(key.g, i), Random.new().read(key.size())) for i in options] 

def construct_proof(encrypted_ballot, key):
    """
    Construye una prueba de cero conocimiento no interactiva con el
    protocolo de Schnorr mediante una transformación Fiat-Shamir.
    
    La implementación de dicho protocolo se detalla en el RFC 8235:
    Schnorr Non-interactive Zero-Knowledge Proof.

    :param encrypted_ballot: La papeleta encriptada.
    :param key: La clave pública de la elección.

    :returns: Una lista con las pruebas criptográficas.
    """
    
    #: choose random v from [0, q-1]
    #v = SystemRandom().randint(0, key.p - 1)


    #: compute V = g^v mod p
    #V = key.g**v % key.p

    #: (INTERACTIVO) choose random c from [0, 2^t-1]
    #:TODO: Hacerlo no interactivo

    # r = v-a*c mod q

    return [1, 2, 3]

def validate_proof(key, ballot, proof):
  pass

lambda x, y, p: []
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

    :param public_key: La clave pública de la elección.
    :param vote_tally: El escrutinio cifrado de votos.
    :param shares: Una lista de secretos compartidos que permiten
        descifrar conjuntamente los votos.

    :returns: El escrutinio de votos descifrado.
    """
    #:COMENTARIO: Idealmente no se reconstruye la clave sino que se usa
    #: algún protocolo de computación distribuida para ejectuar el
    #: cómputo **SIN** reconstruir la clave.
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

    :returns: Una lista.
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
