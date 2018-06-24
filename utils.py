"""
Aquí se encuentra funciones de ayuda varias utilizadas por múltiples
módulos del sistema.
"""

import crypto

def get_final_votes(blockchain):
    pk = blockchain.public_key
    votes = blockchain.votes

    final_tally = []
    options = list(map(lambda v: v.get("options"), votes))

    vote_tally = crypto.tally_votes(pk, options)

    decrypted_tally = crypto.decrypt_vote_tally(pk, vote_tally)
    
    final_tally = []
    for i in decrypted_tally:
        final_tally.append(crypto.consult_decryption_table({pk.x: crypto.vote_lookup_table(pk, 100)}, pk, i))

    return final_tally

def create_new_key_dict(d_list: [dict], k: object) -> dict:
    """
    Crea un nuevo objeto `dict` de una lista de dicts donde las claves
    son un elemento común a los dicts y los valores para cada clave son
    el resto del dict.
    
    :param d_list: Una lista de dicts.
    :param k: El elemento a usar de clave.

    :returns: Un nuevo dict.

    :raises ValueError: Si la clave no se encuentra en algún dict de la
        lista.
    """
    new_dict = {}
    d_list_c = d_list.copy()
    for d in d_list_c:
        try:
            dk = d.pop(k)
        except KeyError:
            raise ValueError("Clave no común a todos los dict de la lista.")
        new_dict.update({dk: d})
    return new_dict
