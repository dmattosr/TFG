"""
Aquí está el conjunto de funciones de criptografía relacionados a la
encripción ElGamal homomórfica y un conjunto de utilidades que permiten
trabajar con ella
"""

import json

from math import ceil, floor, log, sqrt

from gmpy2 import is_prime

from Crypto.PublicKey import ElGamal
from Crypto import Random
from Crypto.Random import random

from time import sleep

# TODO: ¿Parametrizar o fijar?
ELGAMAL_KEYSIZE = 2048

def discrete_log(a, b, n):
    """
    Para un Grupo Ciclico G de orden n, con generador a y un elemento b,
    devuelve un número x satisfaciendo :math:`a^x=b` mediante el
    algoritmo giant-step baby-step.
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

def multiplicative_inverse(n, m):
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

def save_key(key):
    key_dict = {
        "p": key.p,
        "g": key.g,
        "y": key.y,
        "x": key.x,
    }
    with open("key", "a+") as f:
        json.dump(key_dict, f)
        f.write("\n")

def load_keys(filename):
    keys = []
    with open(filename) as f:
        for line in f.readlines():
            k_dict = json.loads(line)
            p = k_dict.get("p")
            g = k_dict.get("g")
            y = k_dict.get("y")
            x = k_dict.get("x")
            keys.append(ElGamal.construct((p, g, y, x)))
    return keys


def generate_ElGamal_key(keysize):
    return ElGamal.generate(keysize, Random.new().read)

def encrypt_for_vote(options, key):
    """
    Encripta una papeleta de votos, en el formato de un array de ints
    que solo pueden ser 0 o 1
    """
    for i in options:
        if i != 0 and i != 1:
            raise ValueError(
                "La papeleta {} está mal formada.".format(str(options))
            )
    return [key.encrypt(pow(key.g, i), Random.new().read(key.size())) for i in options] 


def tally_votes(options_list, key):
    tallied = [[1,1] for i in range(len(options_list[0]))]
    for i in options_list:
        for c in range(len(i)):
            tallied[c][0] *= i[c][0]
            tallied[c][0] %= key.p
            tallied[c][1] *= i[c][1]
            tallied[c][1] %= key.p
    return list(map(lambda x: key.decrypt(x), [tuple(i) for i in tallied]))
    

def generate_lookup_table_vote(key, maxa):
    table = []
    print(key.p)
    for x in range(maxa):
        table.append(pow(key.g, x, key.p))
        print(x)
    return table

def test_tally():
    enc = []
    unenc = []
    a = [1, 0, 0, 0, 0, 0, 0]
    key = generate_ElGamal_key(256)
    print("key generated")

    for i in range(10000):
        random.shuffle(a)
        unenc.append(a[:])

    for i in range(1000):
        unenc.append([0,1,0,0,0,0,0])

    print(unenc, "\n")

    for vote in unenc:
        enc.append(encrypt_for_vote(vote, key))

    print(enc, "\n")

    tallied = tally_votes(enc, key)
    print(tallied, "\n")

    table = generate_lookup_table_vote(key, 10000)
    print(table, "\n")

    print([table.index(i) for i in tallied], "\n")
