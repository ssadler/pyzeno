
"""

Basic Zeno reactor for managing connections and sending and receiving messages.

Implements networking node to send and receive messages.

Works concurrently, will create one lightweight thread for each outgoing connection
and one thread for each incoming connection.

Use case: Get peers

ZenoReactor will only start the server if you tell it to.

> node = ZenoReactor()
> node.start_server()
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
import socket
import struct
import queue
import binascii


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
        self.incoming_queue.get(block=block, timeout=timeout)

    def send(self, dest, data):
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
        gevent.spawn(self.run_server)

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
            self.incoming_queue.put((DROP_PEER, addr))
            sock.close()
            raise

    def handle_conn(self, sock, addr):
        (protocol, port) = recv_struct(sock, "BH")
        assert protocol == b"\0"
        self.incoming_queue.put((NEW_PEER, addr))
        
        while True:
            msg_len = recv_struct(sock, "I")
            msg = recv_bytes(sock, msg_len)
            self.incoming_queue.put((MESSAGE, addr, msg))


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

