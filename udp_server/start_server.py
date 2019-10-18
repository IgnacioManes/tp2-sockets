import collections
import json
import math
import os
import socket
import time

from udp_common import udp_common

class UDPState:
    FRESH_START = 0
    WAITING = 1
    GOT_METADATA = 2
    FILE_RECEIVED = 3

def start_server(server_address, storage_dir):
    # TODO: Implementar UDP server
    print('UDP: start_server({}, {})'.format(server_address, storage_dir))

    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
    
    (server_host, server_port) = server_address

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((server_host, server_port))

        while True:
            handle_connection(sock, server_address, storage_dir)

def handle_handshake(sock, server_address):
    while True:
        time.sleep(2)
        data_raw, addr = udp_common.recv_with_ack(
            sock,
            b'1',
            1024,
            None,
            50,
            expected_seq=50
        )
        print('received metadata and sent ack')
        data_raw_str = data_raw.decode()
        try:
            metadata = json.loads(data_raw_str)
            if isinstance(metadata, collections.Mapping):
                print('metadata')
                print(metadata)
                return (addr, metadata)
        except json.decoder.JSONDecodeError:
            print('Got bogus data, ignoring', data_raw_str)
            pass
        else:
            print('Got bogus data, ignoring', data_raw_str)

def handle_connection(sock, server_address, storage_dir):
    state = UDPState.FRESH_START

    if state == UDPState.FRESH_START:
        (client_addr, metadata) = handle_handshake(sock, server_address)
        state = UDPState.GOT_METADATA

    if state == UDPState.GOT_METADATA:
        filename = metadata['filename']
        dest_path = "{}/{}".format(storage_dir, filename)

        if metadata['action'] == 'u':
            filesize = metadata['filesize']
            udp_common.receive_file(sock, client_addr, dest_path, filesize)
        elif metadata['action'] == 'd':
            filesize = os.path.getsize(dest_path)
            filesize_raw = bytes(str(filesize), 'utf8')
            udp_common.send_with_ack(
                sock,
                client_addr,
                filesize_raw,
                1,
                5,
                1,
                expected_seq=51
            )
            udp_common.send_file(sock, client_addr, dest_path)
