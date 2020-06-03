#!/usr/bin/env python3
import socket
import binascii
import pdb
import sys
import _thread
import time
import datetime

# the very first packet expected is <version byte><port>
# this is the port the peer will attempt to make a connection to
def init_payload(port):
    if port < 16:
        bigend = "000" + str(hex(port)[2:])
    elif port < 256:
        bigend = "00" + str(hex(port)[2:])
    elif port < 4096:
        bigend = "0" + str(hex(port)[2:])
    elif port < 65536:
        bigend = str(hex(port)[2:])
    payload = "00" + bigend
    payload = bytes(payload.encode('utf-8'))
    payload = binascii.unhexlify(payload)
    return(payload)


def parse_peers(data):
    data = data[56:]
    IP_amount = int(data[:2], 16)
    peers = []
    count = 0
    while count < IP_amount:
        if count == 0:
            data = data[16:]
        else:
            data = data[18:]
        len_byte = int(data[:2],16)*2
        data = data[2:]
        IP_hex = data[:len_byte]
        port = int(data[len_byte:len_byte+4], 16)
        data = data[len_byte:]
        ip = binascii.unhexlify(IP_hex).decode('utf-8')
        peers.append((ip, port))
        count += 1
    return(peers)


# each peer is expecting a packet with payload 00000000 every 5 seconds 
# will time out after 20(?) attempts without response
def keepalive(peer, port):
    sends = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sends.connect(peer)
    payload = init_payload(port)

    #while True:
    sends.sendall(payload)
    sends.sendall(binascii.unhexlify(b'00000011e4dfbbb9aeaff2c844181d5f031f2cac00'))
    sends.sendall(binascii.unhexlify(b'00000000'))
    while True:
        time.sleep(5)
        sends.sendall(binascii.unhexlify(b'00000000'))



def listen(port, max_connections):
    s = socket.socket(socket.AF_INET,
                      socket.SOCK_STREAM)
    host = ''
    s.bind((host, port))
    s.listen(max_connections)

    while True:
        clientSocket, addr = s.accept()
        print("replied: ", str(addr))
        if addr[0] in WHITELIST: # FIXME whitelist is a temporary measure until we can detect protocol
            SOCKETS.append(clientSocket)
            _thread.start_new_thread( receive, (clientSocket,) )
        else:
            clientSocket.close()


# not actually used except during debugging
def close_all():
    for s in SOCKETS:
        try:
            s.close()
        except Exception as e:
            print(e)
    sys.exit(0)


def current_time():
    return datetime.datetime.utcfromtimestamp(int(time.time())).strftime('%Y-%m-%d %H:%M:%S')


def receive(sock):
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if data.hex() == '00000000' and SHOW_KEEPALIVE:
                print('[' + current_time() + ']' + str(sock.getpeername()) + ': keepalive\n')
                continue
            if data.hex() == '00000011e4dfbbb9aeaff2c844181d5f031f2cac00':
                print('[' + current_time() + ']' + str(sock.getpeername()) + ': GetPeers\n')
                continue
            if data.hex()[12:48] == 'e4dfbbb9aeaff2c844181d5f031f2cac01':
                print('[' + current_time() + ']' + str(sock.getpeername()) + ': PeerList\n')
                continue
            if data.hex() != '00000000': # FIXME ELIF JANK; need a single function to handle this
                roundid = data.hex()[8:20]
                stepid = data.hex()[20:40]
                print('[' + current_time() + ']' + str(sock.getpeername()) + '\nroundid: ' + roundid + 
                      '\nstepid: ' + stepid + '\nraw:' + data.hex() + '\n')
        except:
            sock.close()
            SOCKETS.remove(sock)

# open connection to seed, requests peerlist, parse peerlist, close connection
def GetPeers(seed, port):
    sout = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sout.connect(seed)
    payload = init_payload(port)

    sout.sendall(payload)
    sout.sendall(binascii.unhexlify(b'00000011e4dfbbb9aeaff2c844181d5f031f2cac00')) # procid + 00 requests peer list
    sout.sendall(binascii.unhexlify(b'00000000')) 

    sin = socket.socket(socket.AF_INET,
                      socket.SOCK_STREAM)
    host = ''
    sin.bind((host, port))
    sin.listen(1)


    clientSocket, addr = sin.accept()
    if addr[0] == seed[0]: # FIXME will fail if another IP attempts connection, needs to keep listening or retry entirely
        while True: # FIXME gets stuck if seed is unreponsive
            data = clientSocket.recv(1024)
            if data.hex()[8:42] == 'e4dfbbb9aeaff2c844181d5f031f2cac01': # proc id + 01 indicates this is the peer list
                peers = parse_peers(data.hex())
                sin.close() # FIXME probably want to maintain a connection to seed node to find newly online peers
                clientSocket.close()
                sout.close()
                return(peers)


SOCKETS = []

# init settings, will make these based on config file or command line args
SHOW_KEEPALIVE = False
seed = ('195.201.20.230', 40440)
py_port = 7777

peers = GetPeers(seed, py_port)
#peers = [('127.0.0.1', 7766)]

WHITELIST = []

# FIXME whitelist is a temporary measure until we can detect protocol reliably
for peer in peers:
    WHITELIST.append(peer[0])

print('PeerList: ', peers)

try:
    _thread.start_new_thread( listen, (py_port, 2, ) )
    time.sleep(1)
    for peer in peers:
        _thread.start_new_thread( keepalive, (peer, py_port, ) )
except Exception as e:
    print(e)
    sys.exit("Error: unable to start listen thread")

# FIXME
# Need to work out how to gracefully kill connections, for now am usng close_all() function in pdb shell 
pdb.set_trace()