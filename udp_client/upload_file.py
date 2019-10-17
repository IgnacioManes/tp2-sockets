import json
import os
import socket

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

    seq = 0
    with open(src, 'rb') as f:
      data = f.read(25)
      while data:
        ba1 = bytes([seq])
        print(seq)
        print(ba1)
        ba2 = bytearray(data)
        ba = ba1 + ba2
        print(len(ba))
        sock.sendto(ba, server_address)
        data = f.read(25)
        seq += 1
    print('Successfully sent the file')
  pass
