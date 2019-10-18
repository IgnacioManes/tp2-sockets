import json
import os
import socket
import sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from udp_common import udp_common

def upload_file(server_address, src, name):
  # TODO: Implementar UDP upload_file client
  print('UDP: upload_file({}, {}, {})'.format(server_address, src, name))

  (server_host, server_port) = server_address
  with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    filesize = os.path.getsize(src)
    message = {
      "action": "u",
      "filename": name,
      "filesize": filesize,
    }
    message_json = json.dumps(message)
    sock.sendto(message_json.encode(), server_address)

    server_ack, addr = sock.recvfrom(1)

    udp_common.send_file(sock, server_address, src)
