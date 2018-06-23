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
