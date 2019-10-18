import json
import os
import socket
import sys
import time

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from udp_common import udp_common

def download_file(server_address, name, dst):
  # TODO: Implementar UDP download_file client
  print('UDP: download_file({}, {}, {})'.format(server_address, name, dst))
  (server_host, server_port) = server_address
  with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    message = {
      "action": "d",
      "filename": name,
    }
    message_json = json.dumps(message)

    udp_common.send_with_ack(
        sock,
        server_address,
        message_json.encode(),
        1,
        5,
        50,
        expected_seq=50
    )
    print('sent metadata and got ack')

    server_filesize_raw, addr = udp_common.recv_with_ack(
        sock,
        b'1',
        1024,
        5,
        51,
        expected_seq=51
    )

    server_filesize = int(str(server_filesize_raw, 'utf8'))

    print('got filesize {}'.format(server_filesize))

    udp_common.receive_file(sock, server_address, dst, int(server_filesize))
  pass
