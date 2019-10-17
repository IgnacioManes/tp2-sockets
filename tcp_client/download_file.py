import socket
from struct import *
import os


def store_file(sock, dst, file_name):
    data_size = len(file_name.encode())
    sock.send(pack("h", data_size))
    sock.send(file_name.encode())
    directory = os.path.dirname(dst)
    if not os.path.exists(f'{directory}'):
        os.makedirs(f'{directory}')
    with open(f"{dst}", 'wb') as f:
        while True:
            data = sock.recv(1024)
            if data:
                f.write(data)
            else:
                print('No more data recv')
                break
    print('Successfully get the file')


def download_file(server_address, name, dst):
    # TODO: Implementar TCP download_file client
    print('TCP: download_file({}, {}, {})'.format(server_address, name, dst))
    (server_host, server_port) = server_address
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(server_address)
        sock.send(b'd')
        store_file(sock, dst, name)
