import json
import os
import socket

class UDPState:
    FRESH_START = 0
    WAITING = 1
    GOT_METADATA = 2
    FILE_RECEIVED = 3

def store_file(sock, server_address, storage_dir, metadata):
    print(metadata)
    with open("{}/{}".format(storage_dir, metadata['filename']), 'wb') as f:
        while True:
            data = sock.recv(1025)
            seq = int(data[0])
            file_content = data[1:]
            print(len(data))
            print(seq)
    print('Successfully get the file')

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
  pass

def handle_handshake(sock, server_address):
  data_raw, addr = sock.recvfrom(1024)
  data_raw_str = data_raw.decode()
  metadata = json.loads(data_raw_str)
  sock.sendto(b'1', addr)
  return (addr, metadata)

def handle_connection(sock, server_address, storage_dir):
  state = UDPState.FRESH_START

  if state == UDPState.FRESH_START:
    (addr, metadata) = handle_handshake(sock, server_address)
    state = UDPState.GOT_METADATA
  
  if state == UDPState.GOT_METADATA:
    if metadata['action'] == 'u':
      store_file(sock, addr, storage_dir, metadata)
    elif metadata['action'] == 'd':
      send_file(sock, addr, storage_dir, metadata)
