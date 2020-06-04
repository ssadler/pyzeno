
"""

Basic Zeno node for p2p usage.

Implements server to receive connections and also a method to send connections.

Works concurrently, will create one lightweight thread for each outgoing connection
and one thread for each incoming connection.

Use case: Accept incoming connections

ZenoNode will only start the server if you tell it to.

> node = ZenoNode()
> node.start_all()


Use case: flood a node

ZenoNode itself is well behaved, it will only create one outgoing connection for each peer.
But, you could create a bunch of them:

> nodes = []
> for i in range(100):
>     node = ZenoNode()
>     node.send("127.0.0.1:40445", some_pid, "blagarbage")
>     nodes.append(node)


"""


import gevent.monkey
gevent.monkey.patch_all()   # This will replace all blocking I/O interfaces with Gevent
                            # enabled ones, to enable cooperative lightweight threads.

import gevent
import gevent.server
import socket
import struct
import queue
import binascii


PEER_CONTROLLER_PID = binascii.unhexlify(b"e4dfbbb9aeaff2c844181d5f031f2cac")
GET_PEERS = "\0"


class ZenoNode:
    def __init__(self, seeds,
            listen_addr="0.0.0.0",
            listen_port=40440,
            keepalive_interval=5):
        self.seeds = seeds
        self.listen_addr = listen_addr
        self.listen_port = listen_port
        self.forwarders = {}
        self.keepalive_interval=5

    def send(self, dest, pid, msg):
        return self._send(dest, pid + msg)

    def _send(self, dest, data):
        # You won't run into a race condition here because Gevent is single threaded
        # It switches between lightweight threads only when they call an I/O operation
        # Otherwise you would need locks everywhere
        # It's beautiful
        forwarder = self.forwarders.get(dest)
        if not forwarder:
            forwarder = queue.Queue()
            gevent.spawn(self.wrap_run_fowarder, dest, forwarder)
            self.fowarders[dest] = forwarder
        self.forwarder.put(data)

    def run_refresh_peers(self):
        while True:
            for seed in self.seeds:
                self.send(seed, peer_controller_pid, GET_PEERS)

            time.sleep(60)

    def wrap_run_forwarder(self, dest, queue):
        try:
            self.run_forwarder(dest, queue)
        except:
            print("Fowarder for %s died" % dest)
            del self.forwarders[dest]
            raise

    def run_forwarder(self, dest, queue):
        sends = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer = dest.split(':')
        peer[1] = int(peer[1])
        sends.connect(peer)

        while True:
            try:
                msg = queue.get(timeout=self.keepalive_interval)
                if msg == ("quit",):
                    break
                packet = struct.pack("I", len(msg)) + msg
                sends.sendall(packet)
            except queue.Empty:
                sends.sendall(b"\0\0\0\0")

    def start(self):
        self.start_server()
        self.start_refresh_peers()

    def start_server(self):
        gevent.spawn(self.run_server)

    def start_refresh_peers(self):
        gevent.spawn(self.run_refesh_peers)

    def run_server(self):
        pool = Pool(1000)
        listen = (self.listen_addr, self.listen_port)
        server = StreamServer(listen, self.wrap_handle_conn, spawn=pool)
        server.serve_forever()

    def wrap_handle_conn(self, sock, addr):
        try:
            self.handle_conn(sock, addr)
        except:
            print("Exception handling connection: %" % addr)
            self.notify_drop_peer(addr)
            sock.close()
            raise

    def handle_conn(self, sock, addr):
        (protocol, port) = recv_struct(sock, "BH")
        assert protocol == b"\0"
        self.node.notify_new_peer(self.addr, port)
        
        while True:
            msg_len = recv_struct(sock, "I")
            msg = recv_bytes(sock, msg_len)
            self.node.on_message(msg)

    def notify_new_peer(self, peer):
        print("New peer: %s" % peer)

    def notify_drop_peer(self, peer):
        print("Drop peer: %s" % peer)


# Receive data using struct format
# https://docs.python.org/3/library/struct.html#format-characters
def recv_struct(sock, fmt):
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, recv_bytes(size))

def recv_bytes(sock, n):
    b = b""
    while True:
        length = length(b)
        if length == n:
            break
        b += sock.recv(n-length)
    return b

