
from zeno.reactor import *
from zeno.round import *
from zeno.utils import *
from zeno.codec import *


"""
This is a light node for Zeno. It can peer, decode the incoming packets and send packets
but it does not know how to make the topic hashes or take part in the consensus
process.
"""


PEER_CONTROLLER_PID = to_bin("e4dfbbb9aeaff2c844181d5f031f2cac")


class ZenoMonitorNode(ZenoReactor):
    def get_event(self, *args, keep_data=False, **kwargs):
        evt = super(ZenoMonitorNode, self).get_event(*args, **kwargs)
        if evt['type'] != MESSAGE:
            return evt
        data = evt['data']
        pid = data[:16]
        if len(pid) < 16:
            evt['invalid'] = True
        else:
            if not keep_data:
                del evt['data']
            evt['pid'] = pid
            if pid == PEER_CONTROLLER_PID:
                evt['peer_event'] = self.decode_peer_event(data[16:], evt)
            else:
                evt['round_event'] = self.decode_round_event(data[16:], evt)
        return evt
    
    def send_pid(self, node_id, pid, msg):
        self.send(node_id, to_bin(pid) + msg)

    def decode_peer_event(self, data, evt):
        parser = Parser(data)
        return PeerControllerCodec().decode(parser)

    def decode_round_event(self, data, evt):
        parser = Parser(data)
        return SignedRoundMessageCodec().decode(parser)


class NodeIdCodec(RecordCodec):
    ITEMS = [
        ("addr", StrCodec()),
        ("port", StructSingleCodec(">H"))
    ]
    def decode(self, parser):
        return "%(addr)s:%(port)s" % super(NodeIdCodec, self).decode(parser)


class PeerControllerCodec(UnionCodec):
    ITEMS = [
        ("getpeers", UnitCodec()),
        ("peers", SetCodec(NodeIdCodec()))
    ]
