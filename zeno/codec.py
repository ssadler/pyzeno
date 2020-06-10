
import struct


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
    def __init__(self, members=None):
        if members:
            self.MEMBERS = members

    def decode(self, parser):
        out = {}
        (type_id,) = parser.unpack(">B")
        return self.choose(type_id, parser)

    def choose(self, type_id, parser):
        if type_id > len(self.MEMBERS) - 1:
            raise ValueError("%s: invalid union type id: %s" % (self.__class__.__name__, type_id))

        member = self.MEMBERS[type_id]
        return {member[0]: member[1].decode(parser)}

class UnitCodec:
    def decode(self, _parser):
        return ()

class ListCodec:
    def __init__(self, inner):
        self.inner = inner

    def decode(self, parser):
        (length,) = parser.unpack("!Q")
        out = []
        for _ in range(length):
            out.append(self.inner.decode(parser))
        return out

class SetCodec(ListCodec):
    def decode(self, parser):
        return set(super(SetCodec, self).decode(parser))

class BufCodec:
    def decode(self, parser):
        (length,) = parser.unpack("!Q")
        return parser.take(length)

class StrCodec(BufCodec):
    def decode(self, parser):
        return super(StrCodec, self).decode(parser).decode()

class RecordCodec:
    def decode(self, parser):
        out = {}
        for (name, codec) in self.MEMBERS:
            out[name] = codec.decode(parser)
        return out

class StructSingleCodec:
    def __init__(self, fmt):
        self.fmt = fmt

    def decode(self, parser):
        return parser.unpack(self.fmt)[0]

class MaybeCodec:
    def __init__(self, inner):
        self.inner = inner

    def decode(self, parser):
        go = parser.unpack(">B")
        if go:
            return self.inner.decode(parser)

class FixedBufCodec:
    def __init__(self, size):
        self.size = size

    def decode(self, parser):
        return parser.take(self.size)
