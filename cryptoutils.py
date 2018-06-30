from math import ceil, log, sqrt

from shamir import _divmod

def discrete_log(a, b, n):
    """
    Resuelve el problema del logaritmo discreto mediante el
    algoritmo *baby-step giant-step*.

    La definición teórica es: para un Grupo Ciclico G de orden n, con
    generador a y un elemento b, devuelve un número x satisfaciendo
    :math:`a^x=b`.

    Esta función está intencionada a ser usada en números pequeños,
    como por ejemplo números en el orden de los millones que resultan
    de las votaciones.

    :param a: El generador.
    :param b: El elemento para el cual se calcula el logaritmo
        discreto.
    :param n: El orden del grupo cíclico.

    :returns: El logaritmo discreto de b base a en el grupo cíclico G o
        -1 si no existe.
    """
    
    m = ceil(sqrt(n))

    trial = []

    for j in range(0, m):
        trial.append((j, pow(a, j, n)))

    a_m = n + _divmod(1, pow(a, m, n), n)

    y = b

    for i in range(0, m):
        for first, second in trial:
            if second == y:
                return (i * m) + first
        y *= a_m
        y %= n

    return "-1"
