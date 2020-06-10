from zeno.monitor import *
import binascii


peer_controller_pid = binascii.unhexlify('e4dfbbb9aeaff2c844181d5f031f2cac')


node = ZenoMonitorNode()
node.start()
node.send("127.0.0.1:40441", peer_controller_pid + b"\0")
while True:
    print("event: ", node.get_event())
