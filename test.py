from zeno.monitor import *
import binascii
import pprint


node = ZenoMonitorNode()
node.start()
node.send("127.0.0.1:40441", PEER_CONTROLLER_PID + b"\0")
while True:
    pprint.pprint(node.get_event())

