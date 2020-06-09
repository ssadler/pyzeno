
"""

Basic Zeno reactor for managing connections and sending and receiving messages.

Implements networking node to send and receive messages.

Works concurrently, will create one lightweight thread for each outgoing connection
and one thread for each incoming connection.

Use case: Get peers

ZenoReactor will only start the server if you tell it to.

> node = ZenoReactor()
> node.start()
> node.send("127.0.0.1:7766", peer_controller_pid + "\0")
> print(node.get_event())


Use case: flood a node

ZenoReactor itself is well behaved, it will only create one outgoing connection for each peer.
But, you could create a bunch of them:

> nodes = []
> for i in range(100):
>     node = ZenoReactor()
>     node.send("127.0.0.1:40445", "blamessage")
>     nodes.append(node)


"""


import gevent.monkey
gevent.monkey.patch_all()   # This will replace all blocking I/O interfaces with Gevent
                            # enabled ones, to enable cooperative lightweight threads.

import gevent
import gevent.server
import gevent.pool
from gevent import queue
import logging
import socket
import struct


NEW_PEER = "new_peer"
DROP_PEER = "drop_peer"
MESSAGE = "msg"


class ZenoReactor:
    def __init__(self,
            listen_addr="0.0.0.0",
            listen_port=7777,
            keepalive_interval=5):
        self.listen_addr = listen_addr
        self.listen_port = listen_port
        self.forwarders = {}
        self.keepalive_interval=5
        self.incoming_queue = queue.Queue()

    def get_event(self, block=True, timeout=None):
        return self.incoming_queue.get(block=block, timeout=timeout)

    def send(self, nodeid, data):
        # You won't run into a race condition here because Gevent is single threaded
        # It switches between lightweight threads only when they call an I/O operation
        # Otherwise you would need locks everywhere
        # It's beautiful
        forwarder = self.forwarders.get(nodeid)
        if not forwarder:
            peer_ip, peer_port = nodeid.split(':')
            dest = (peer_ip, int(peer_port))
            forwarder = queue.Queue()
            self.forwarders[nodeid] = forwarder
            gevent.spawn(self.wrap_run_forwarder, dest, forwarder)
        forwarder.put(data)

    def wrap_run_forwarder(self, dest, fwdq):
        try:
            self.run_forwarder(dest, fwdq)
        except Exception as e:
            logging.warn("Fowarder %s died: %s" % (dest, e))
            #raise
        finally:
            del self.forwarders["%s:%s" % dest]

    def run_forwarder(self, dest, fwdq):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(dest)

        # Send header
        sock.send(b'\0' + struct.pack('>H', self.listen_port))

        while True:
            try:
                msg = fwdq.get(timeout=self.keepalive_interval)
                if msg == ("quit",):
                    break
                packet = struct.pack(">I", len(msg)) + msg
                sock.sendall(packet)
            except queue.Empty:
                sock.sendall(b"\0\0\0\0")

    def start(self):
        gevent.spawn(self.run_server)

    def run_server(self):
        pool = gevent.pool.Pool(1000)
        listen = (self.listen_addr, self.listen_port)
        server = gevent.server.StreamServer(listen, self.wrap_handle_conn, spawn=pool)
        server.serve_forever()

    def wrap_handle_conn(self, sock, addr):
        try:
            self.handle_conn(sock, addr)
        except Exception as e:
            logging.warn("Conn %s: %s" % (addr, e))
            self.incoming_queue.put((DROP_PEER, show_node_id(addr)))
            raise
        finally:

            sock.close()

    def handle_conn(self, sock, addr):
        (protocol, port) = recv_struct(sock, ">BH")
        assert protocol == 0, ("Strange protocol: %s" % protocol)
        self.incoming_queue.put((NEW_PEER, show_node_id(addr)))
        
        while True:
            (msg_len,) = recv_struct(sock, ">I")
            msg = recv_bytes(sock, msg_len)
            self.incoming_queue.put((MESSAGE, show_node_id(addr), msg))

def show_node_id(addr):
    return "%s:%s" % addr

# Receive data using struct format
# https://docs.python.org/3/library/struct.html#format-characters
def recv_struct(sock, fmt):
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, recv_bytes(sock, size))

def recv_bytes(sock, n):
    b = b""
    while True:
        length = len(b)
        if length == n:
            break
        b += sock.recv(n-length)
    return b

