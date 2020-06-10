
import binascii

def to_bin(s):
    if type(s) == bytes:
        return s
    return binascii.unhexlify(s)

def from_bin(s):
    if type(s) != bytes:
        return s
    return binascii.hexlify(s)

