"""
Lo siguiente es una adaptación de un código que se encuentra en el
dominio público. Aquí adelante se encuentra intacto el mensaje de
copyright original:

    The following Python implementation of Shamir's Secret Sharing is
    released into the Public Domain under the terms of CC0 and OWFa:
    https://creativecommons.org/publicdomain/zero/1.0/
    http://www.openwebfoundation.org/legal/the-owf-1-0-agreements/owfa-1-0

    See the bottom few lines for usage. Tested on Python 2 and 3.

Las modificaciones adicionales están bajo una licencia MIT.
"""

from random import SystemRandom
from functools import reduce

MERSENNE_PRIME = 2**521 - 1
"""
Definimos el número primo a utilizar para la seguridad. Debe ser un
número primo de Mersenne. Aquí utilizamos el número 13, el primero
estrictamente mayor que nuestra clave privada.
"""

def _eval_at(poly, x, prime):
    """
    evaluates polynomial (coefficient tuple) at x, used to generate a
    shamir pool in make_random_shares below.
    """
    accum = 0
    for coeff in reversed(poly):
        accum *= x
        accum += coeff
        accum %= prime
    return accum


def make_shares(key, minimum, shares, prime=MERSENNE_PRIME):
    '''
    Generates a random shamir pool, returns the secret and the share
    points.
    '''
    if minimum > shares:
        raise ValueError("pool secret would be irrecoverable")
    poly = [key.x] + [SystemRandom().randint(0, prime) for i in range(minimum)]
    shares = [(i, _eval_at(poly, i, prime))
              for i in range(1, shares + 1)]
    return shares


def _extended_gcd(a, b):
    '''
    division in integers modulus p means finding the inverse of the
    denominator modulo p and then multiplying the numerator by this
    inverse (Note: inverse of A is B such that A*B % p == 1) this can
    be computed via extended Euclidean algorithm
    http://en.wikipedia.org/wiki/Modular_multiplicative_inverse#Computation
    '''

    x = 0
    last_x = 1
    y = 1
    last_y = 0
    while b != 0:
        quot = a // b
        a, b = b,  a%b
        x, last_x = last_x - quot * x, x
        y, last_y = last_y - quot * y, y
    return last_x, last_y


def _divmod(num, den, p):
    '''
    compute num / den modulo prime p

    To explain what this means, the return value will be such that
    the following is true: den * _divmod(num, den, p) % p == num
    '''
    inv, _ = _extended_gcd(den, p)
    return num * inv


def _lagrange_interpolate(x, x_s, y_s, p):
    '''
    Find the y-value for the given x, given n (x, y) points;
    k points will define a polynomial of up to kth order
    '''
    k = len(x_s)
    assert k == len(set(x_s)), "points must be distinct"
    PI = lambda vals: reduce(lambda x, y: x*y, vals)
    nums = []  # avoid inexact division
    dens = []
    for i in range(k):
        others = list(x_s)
        cur = others.pop(i)
        nums.append(PI(x - o for o in others))
        dens.append(PI(cur - o for o in others))
    den = PI(dens)
    num = sum([_divmod(nums[i] * den * y_s[i] % p, dens[i], p)
               for i in range(k)])
    return (_divmod(num, den, p) + p) % p


def recover_secret(shares, prime=MERSENNE_PRIME):
    """
    Recupera el secreto a partir de los shares (los puntos (x, y) del
    polinomio).
    """
    if len(shares) < 2:
        raise ValueError("Son necesarios al menos dos shares")
    x_s, y_s = zip(*shares)
    return _lagrange_interpolate(0, x_s, y_s, prime)
