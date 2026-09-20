import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


def compute_sha256(data_bytes: bytes) -> str:
    return hashlib.sha256(data_bytes).hexdigest()


def encrypt_file(file_bytes: bytes):
    key = get_random_bytes(32)
    cipher = AES.new(key, AES.MODE_CBC)
    ciphertext = cipher.encrypt(pad(file_bytes, AES.block_size))
    return ciphertext, key, cipher.iv


def decrypt_file(ciphertext: bytes, key: bytes, iv: bytes):
    key = bytes(key)
    iv = bytes(iv)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)
