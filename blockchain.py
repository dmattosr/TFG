"""
Aquí se encuentra la definición de las clases necesarias para el uso de
la blockchain.
"""

import json
import crypto

class Blockchain:
    """
    Esta es la BLOCKCHAAAAAIN.

    .. todo::
        Hacer el genesis block. Debería tener:

        - Fecha de inicio.
        - Fecha de caducidad.
        - Clave pública.
        - Más cosas, probablemente.

    """

    def __init__(self, end_date):
        """
        .. todo::
            El timestamp debería estar firmado digitalmente por alguna
            autoridad
        """
        self.start_timestamp = time.time()
        self.end_timestamp = end_date
        self.public_key = 3

    def serialize(self):
        return {

        }
        
    def __repr__(self):
        return "blep"

    def __str__(self):
        return "blep"