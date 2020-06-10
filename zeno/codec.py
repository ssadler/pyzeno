
from math import log, ceil
import struct

from zeno.utils import *


class Parser:
    def __init__(self, data):
        self.data = data

    def unpack(self, fmt):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.take(size))

    def take(self, size):
        if len(self.data) < size:
            raise ValueError("not enough data to take: %s" % size)
        out = self.data[:size]
        self.data = self.data[size:]
        return out

class UnionCodec:
    def __init__(self, items=None):
        if items:
            self.ITEMS = items

    def decode(self, parser):
        out = {}
        (type_id,) = parser.unpack(">B")
        return self.choose(type_id, parser)

    def choose(self, type_id, parser):
        if type_id > len(self.ITEMS) - 1:
            raise ValueError("%s: invalid union type id: %s" %
                             (self.__class__.__name__, type_id))

        (name, codec) = self.ITEMS[type_id]
        return {name: codec.decode(parser)}

    def encode(self, data):
        (i, encoded) = self.unchoose(data)
        return bytes([i]) + encoded

    def unchoose(self, data):
        for (i, (name, codec)) in enumerate(self.ITEMS):
            if name in data:
                return (i, codec.encode(data[name]))
        raise ValueError("no keys found in provided record") # Could be a beter error message

class UnitCodec:
    def decode(self, _parser):
        return ()

    def encode(self, a):
        assert a in (None, ()), ("Cannot encode to (): %s" % repr(a))
        return b""

class ListCodec:
    def __init__(self, inner):
        self.inner = inner

    def decode(self, parser):
        (length,) = parser.unpack("!Q")
        out = []
        for _ in range(length):
            out.append(self.inner.decode(parser))
        return out

    def encode(self, items):
        out = struct.pack('!Q', len(items))
        return out + b"".join(inner.encode(i) for i in items)

class SetCodec(ListCodec):
    def decode(self, parser):
        return set(super(SetCodec, self).decode(parser))

class BufCodec:
    def decode(self, parser):
        (length,) = parser.unpack("!Q")
        return parser.take(length)

    def encode(self, buf):
        out = struct.pack('!Q', len(items))
        return out + buf

class StrCodec(BufCodec):
    def decode(self, parser):
        return super(StrCodec, self).decode(parser).decode()

    def encode(self, s):
        return super(StrCodec, self).encode(s.encode())

class RecordCodec:
    def __init__(self, items=None):
        if items:
            self.ITEMS = items

    def decode(self, parser):
        out = {}
        for (name, codec) in self.ITEMS:
            out[name] = codec.decode(parser)
        return out

    def encode(self, record):
        out = "".join(codec.encode(record[k]) for (k, codec) in self.ITEMS)

class StructSingleCodec:
    def __init__(self, fmt):
        self.fmt = fmt

    def decode(self, parser):
        return parser.unpack(self.fmt)[0]

    def encode(self, i):
        return struct.pack(self.fmt, i)

class MaybeCodec:
    def __init__(self, inner):
        self.inner = inner

    def decode(self, parser):
        (go,) = parser.unpack(">B")
        if go == 1:
            return self.inner.decode(parser)

    def encode(self, m):
        return b"\1" + self.inner(m) if m else b"\0"

class FixedBufCodec:
    def __init__(self, size):
        self.size = size

    def decode(self, parser):
        return parser.take(self.size)

    def encode(self, buf):
        return buf

class BigIntCodec:
    def decode(self, parser):
        (n,) = parser.unpack(">B")
        return int.from_bytes(parser.take(n), 'big')

    def encode(self, i):
        return int(i).to_bytes(ceil(log(i, 256)), 'big')

