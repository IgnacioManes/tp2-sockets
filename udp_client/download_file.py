import json
import os
import socket
import sys

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
    sock.sendto(message_json.encode(), server_address)

    server_ack, addr = sock.recvfrom(1)
    server_filesize_raw, addr = sock.recvfrom(1024)

    server_filesize = int(str(server_filesize_raw, 'utf8'))

    udp_common.receive_file(sock, server_address, dst, int(server_filesize))
  pass
