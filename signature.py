import Cryptodome.PublicKey.ECC as ECC
import Cryptodome.Signature.DSS as DSS
from Cryptodome.Hash import SHA256
from base64 import urlsafe_b64encode

CURVE = "P-256"
MODE = "fips-186-3"
FORMAT = "DER"

def generate_signature():
    """
    Genera una clave ECDSA.

    :return: Una clave ECDSA.
    """
    return ECC.generate(curve=CURVE)


def sign(key, msg):
    """
    Firma un mensaje digitalmente con una clave privada.

    :param key: Una clave privada.
    :param msg: Un mensaje a firmar.

    :return: La firma digital del mensaje.

    :raise ValueError: Si la clave no tiene componente privada.
    """
    if not key.has_private():
        raise ValueError("La firma digital no tiene componente privada")
    msg_hash = SHA256.new(msg)
    dss = DSS.new(key=key, mode=MODE)
    return dss.sign(msg_hash)


def verify(key, signature, msg):
    """
    Verifica la validez de la firma sobre un mensaje.

    :param key: Una clave del par público-privado que pueda verificar
        la firma.
    :param signature: La firma digital.
    :param msg: El mensaje firmado.

    :return: `True` si la firma es válida, `False` en cualquier otro caso.
    """
    try:
        dss = DSS.new(key=key, mode=MODE)
        dss.verify(signature=signature, msg_hash=SHA256.new(msg))
        return True
    except ValueError:
        return False


def address(key):
    """
    Devuelve una firma digital apropiada para ser usada en una papeleta.
    Es el resultado de firmar el hash de la clave pública de la clave
    privada correspondiente.
    El nombre *address* viene de la similitud de este mecanismo con el
    utilizado por Bitcoin para generar direcciones para las
    transacciones.

    :param key: La clave con componente privada.

    :returns: La firma digital del hash de la clave pública
        correspondiente (la dirección, *address*).
    """
    return sign(key, key.public_key().export_key(format="DER"))


def is_valid_signature(signature, signature_list):
    """
    Dada una firma digital presente en una papeleta, permite
    contrastarla con la lista de votantes para saber si la
    firma es válida.
    
    :param signature: La firma digital.
    :param signature_list: La lista de claves públicas de los votantes

    :returns: `True` si la firma es válida, `False` en cualquier otro
        caso.
    """
    hashes = [sig.export_key(format="DER") for sig in signature_list]
    for pk, h in zip(signature_list, hashes):
        if verify(pk, signature, h):
            return True
    return False
