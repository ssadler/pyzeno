
from zeno.reactor import *
from zeno.utils import *
from zeno.codec import *


"""
This is a light node for Zeno. It can peer, decode the incoming packets and send packets
but it does not know how to make the topic hashes or take part in the consensus
process.
"""


PEER_CONTROLLER_PID = to_bin("e4dfbbb9aeaff2c844181d5f031f2cac")

INVALID = "invalid"


class ZenoMonitorNode(ZenoReactor):
    def get_event(self, *args, **kwargs):
        evt = super(ZenoMonitorNode, self).get_event(*args, **kwargs)
        if evt['type'] != MESSAGE:
            return evt
        data = evt['data']
        pid = data[:16]
        if len(pid) < 16:
            return (INVALID, evt)
        if pid == PEER_CONTROLLER_PID:
            evt['peer_event'] = self.decode_peer_event(data[16:], evt)
        else:
            evt['round_event'] = self.decode_round_event(data[16:], evt)
        return evt

    def decode_peer_event(self, data, evt):
        parser = Parser(data)
        return PeerControllerCodec().decode(parser)

    def decode_round_event(self, data, evt):
        parser = Parser(data)
        return SignedRoundMessageCodec().decode(parser)


class NodeIdCodec(RecordCodec):
    MEMBERS = [
        ("addr", StrCodec()),
        ("port", StructSingleCodec(">H"))
    ]
    def decode(self, parser):
        return "%(addr)s:%(port)s" % super(NodeIdCodec, self).decode(parser)


class PeerControllerCodec(UnionCodec):
    MEMBERS = [
        ("getpeers", UnitCodec()),
        ("peers", SetCodec(NodeIdCodec()))
    ]

class StepMessageCodec(UnionCodec):
    def decode(self, parser):
        major, minor = parser.unpack(">BB")
        out = self.choose(major, parser)
        out['minor'] = minor
        return out

class KmdToEthStepCodec(StepMessageCodec):
    MEMBERS = [
        ("0", UnitCodec()),
        ("1", UnitCodec()),
        ("2", UnitCodec()),
        ("3", UnitCodec()),
        ("4", UnitCodec()),
        ("5", UnitCodec()),
        ("6", UnitCodec()),
    ]

class EthToKmdStepCodec(StepMessageCodec):
    MEMBERS = [
        ("0", UnitCodec()),
        ("1", UnitCodec()),
        ("2", UnitCodec()),
        ("3", UnitCodec()),
        ("4", UnitCodec()),
        ("5", UnitCodec()),
    ]

class StatsToKmdStepCodec(StepMessageCodec):
    MEMBERS = []


class RoundMessageCodec(UnionCodec):
    MEMBERS = [
        ("kmdToEth", KmdToEthStepCodec()),
        ("ethToKmd", EthToKmdStepCodec()),
        ("statsToKmd", StatsToKmdStepCodec()),
    ]

class SignedRoundMessageCodec(RecordCodec):
    MEMBERS = [
        ('signature', FixedBufCodec(65)),
        ('inner', MaybeCodec(RoundMessageCodec()))
    ]


