"""
Aquí se encuentra funciones de ayuda varias utilizadas por múltiples
módulos del sistema.
"""

import time

import crypto

# GLOBALS: variables globales de ayuda para el programa
# Logger: Utilizado para funciones de información en todo el sistema.
LOGGER_FORMAT = "%(loglevel)s"


def verify_vote(key, chain, election_id, options, proofs, signature):
    """
    Para contar un voto como correcto hay que verificar:

    - El id de elección pertenece a una elección ya creada y todavía
      activa, y está en el formato correcto.

    - Las opciones son una lista, con tamaño igual al número de
      opciones posibles, donde cada elemento es un texto cifrado en el
      esquema ElGamal y que representa un "`1`" o un "`0`".

    - Las pruebas (:param proofs:) son una serie de pruebas de cero
      conocimiento no interactivas que verifican que:
      - Todos los elementos en la lista de opciones encriptan un 0 o un
        1.
      - Como máximo existe un único 1 en la lista que representa el
        voto.
      
    - La firma digital representa que el emisor del voto fue alguien
      autorizado en la votación.

    """
    pass
    #return (id_check and options_check and proofs_check and signature_check)


def time_performance(func, *args):
    """
    Informa sobre el tiempo de ejecución real de una función.

    :param func: La función a ejecutar
    """
    start_time = time.time()
    func(*args)
    return time.time() - start_time
