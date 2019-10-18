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


def handle_connection(sock, server_address, storage_dir):
    try:
        # Fresh start
        (client_addr, metadata) = handle_handshake(sock, server_address)
        state = UDPState.GOT_METADATA

        # At this point we have the metadata
        # of the action the client wants to do.
        # It will always involve a file, so parse that
        filename = metadata['filename']
        dest_path = "{}/{}".format(storage_dir, filename)

        if metadata['action'] == 'u':
            # Upload
            filesize = metadata['filesize']
            udp_common.receive_file(sock, client_addr, dest_path, filesize)
        elif metadata['action'] == 'd':
            # Download
            try:
                filesize = os.path.getsize(dest_path)
                filesize_raw = bytes(str(filesize), 'utf8')
                udp_common.send_with_ack(
                    sock,
                    client_addr,
                    filesize_raw,
                    1,
                    5,
                    1,
                    expected_seq=1
                )
                udp_common.send_file(sock, client_addr, dest_path)
            except FileNotFoundError:
                print("Requested file was not found. Aborting...")
            except udp_common.NoACKException:
                print("Did not get a correct ACK. Aborting...")

    except udp_common.WrongSeqException:
        print("Got an unexpected sequence number. Aborting...")
        pass

def handle_handshake(sock, server_address):
    while True:
        try:
            data_raw, addr = udp_common.recv_with_ack(
                sock,
                b'1',
                1024,
                None,
                0,
                expected_seq=0
            )
            print('received metadata and sent ack')
            data_raw_str = data_raw.decode()
            metadata = json.loads(data_raw_str)
            if isinstance(metadata, collections.Mapping):
                print('metadata')
                print(metadata)
                return (addr, metadata)
        except json.decoder.JSONDecodeError:
            print('Got bogus data, ignoring')
            pass
        except udp_common.WrongSeqException:
            print("Got an unexpected sequence number. Continuing...")
            pass
        except udp_common.NoACKException:
            print("Did not get a correct ACK. Continuing...")
            pass