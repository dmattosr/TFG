"""
Aquí está el conjunto de funciones de criptografía relacionados a la
encripción ElGamal homomórfica y un conjunto de utilidades que permiten
trabajar con ella
"""
from math import ceil, floor, sqrt

from Crypto.PublicKey import ElGamal
from Crypto import Random
from Crypto.Random import random

# TODO: ¿Parametrizar o fijar?
ELGAMAL_KEYSIZE = 2048

def discrete_log(a, b, n):
    """
    Para un Grupo Ciclico G de orden n, con generador a y un elemento b
    Devuelve un número x satisfaciendo $a^x=b$.
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
    Computa $n^{-1} (mod n)$ usando el algoritmo de Gauss
    Si el modulo no es primo no sirve, verificar de alguna manera
    """
    num = 1
    denum = n
    for i in range(modulo):
        x = ceil(modulo/denum)
        num = (x * num) % modulo 
        denum = (x * denum) % modulo
        if denum == 1:
            return num
    return -1

def is_prime(number) -> bool:
    """
    Determina si un número es primo basado en un método probabilístico
    ..todo: Implementar con método probabilístico
    """
    return True

def f():
    keysize = 8
    key = ElGamal.generate(keysize, Random.new().read)
    g = key.g
    p = key.p

    x = pow(g, 3, p) # g^3 (mod p)
    y = pow(g, 4, p) # g^4 (mod p)

    xc = key.encrypt(x, Random.new().read(1))
    print("xc", xc)
    yc = key.encrypt(y, Random.new().read(1))
    print("yc", yc)
    sumcrypt = (xc[0] + yc[0], xc[1] + yc[1])
    print(sumcrypt)
    decrypted = key.decrypt(sumcrypt)
    print("g", g)
    print("decrypted:", decrypted)
    print("p", p)
    print(discrete_log(g, decrypted, p))

def generate_and_save_key(keysize):
    key = ElGamal.generate(keysize, Random.new().read)
    with open("key", "a+") as f:
        print(str(key.p), file=f)
        print(str(key.g), file=f)
        print(str(key.y), file=f)
        print(str(key.x), file=f)

def load_key(filename):
    with open(filename) as f:
        f.readline()

def test():
    keysize = 128
    key = ElGamal.generate(keysize, Random.new().read)
    g = key.g
    p = key.p

    a = 23
    b = 41
    expect = pow(g, a + b, p)

    xc = key.encrypt(pow(g, a, p), Random.new().read(3))
    yc = key.encrypt(pow(g, b, p), Random.new().read(3))
    sumcrypt = (xc[0] * yc[0], xc[1] * yc[1])
    decrypted = key.decrypt(sumcrypt)

    print(g)
    print(decrypted)
    print(p)
    return expect == decrypted
