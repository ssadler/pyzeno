
from zeno.codec import *

class RoundCodec(UnionCodec):
    def decode(self, parser):
        major, minor = parser.unpack(">BB")
        out = self.choose(major - 1, parser)
        out['minor'] = minor
        return out

    def encode(self, item):
        (i, encoded) = self.unchoose(item)
        return struct.pack(">BB", i+1, item['minor']) + codec.encode(item)

class StepMessageCodec(RecordCodec):
    def __init__(self, name, inner):
        inv_items = [
            ("address", FixedBufCodec(20)),
            ("sig", FixedBufCodec(65)),
            (name, inner)
        ]
        self.ITEMS = [
            ("index", BigIntCodec()),
            ("request", BigIntCodec()),
            ("inventory", ListCodec(RecordCodec(inv_items))),
        ]
    
class KmdToEthStepCodec(RoundCodec):

    class EthTxCodec(RecordCodec):
        ITEMS = [
            ("nonce", BigIntCodec()),
            ("value", BigIntCodec()),
            ("to", MaybeCodec(FixedBufCodec(20))),
            ("sig", MaybeCodec(FixedBufCodec(65))),
            ("gasPrice", BigIntCodec()),
            ("gas", BigIntCodec()),
            ("data", BufCodec()),
            ("chainId", StructSingleCodec(">B"))
        ]

    ITEMS = [
        ("1_collectsigs", StepMessageCodec("sighash", FixedBufCodec(32))),
        ("2_proposetx",   StepMessageCodec("tx", MaybeCodec(EthTxCodec()))),
        ("3_confirm",     StepMessageCodec("unit", UnitCodec())),
        ("4_confirm",     StepMessageCodec("unit", UnitCodec())),
        ("5_confirm",     StepMessageCodec("unit", UnitCodec())),
    ]

class OutpointCodec(RecordCodec):
    def __init__(self, fmt=">I"):
        self.ITEMS = [
            ("txid", FixedBufCodec(32)),
            ("n", StructSingleCodec(fmt))
        ]

class MemberUtxo(RecordCodec):
    ITEMS = [
        ("pubkey", FixedBufCodec(33)),
        ("prevout", OutpointCodec()),
    ]

class ChosenUtxo(RecordCodec):
    ITEMS = [
        ("address", FixedBufCodec(20)),
        ("utxo", MemberUtxo()),
    ]

class EthToKmdStepCodec(RoundCodec):

    class BitcoinTxInCodec(RecordCodec):
        class BitcoinScriptCodec:
            def decode(self, parser):
                (length,) = parser.unpack(">B")
                assert length < 250, "TODO: implement varint"
                return parser.take(length)

            def encode(self, script):
                length = len(script)
                assert length < 250, "TODO: implement varint"
                return struct.pack(">B", length) + script

        ITEMS = [
            ("prevout", OutpointCodec("<I")),
            ("script", BitcoinScriptCodec()),
            ("sequence", StructSingleCodec("<I"))
        ]
    
    ITEMS = [
        ("1_collectutxos",  StepMessageCodec("utxo",        MemberUtxo())),
        ("2_proposeutxos",  StepMessageCodec("chosenutxos", MaybeCodec(ListCodec(ChosenUtxo())))),
        ("3_collectinputs", StepMessageCodec("signedinput", MaybeCodec(BitcoinTxInCodec()))),
        ("4_confirm",       StepMessageCodec("unit",        UnitCodec())),
    ]

class StatsToKmdStepCodec(RoundCodec):
    ITEMS = [
        ("1_collectsigs", StepMessageCodec("sighash", FixedBufCodec(32))),
        ("2_proposetx",   UnitCodec()), # TODO: StepMessage("tx", SaplingTxCodec()),
    ]

class RoundMessageCodec(UnionCodec):
    ITEMS = [
        ("kmdToEth", KmdToEthStepCodec()),
        ("ethToKmd", EthToKmdStepCodec()),
        ("statsToKmd", StatsToKmdStepCodec()),
    ]

class SignedRoundMessageCodec(RecordCodec):
    ITEMS = [
        ('signature', FixedBufCodec(65)),
        ('inner', MaybeCodec(RoundMessageCodec()))
    ]

