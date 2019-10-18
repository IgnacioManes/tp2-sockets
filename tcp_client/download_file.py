import socket
from struct import *
import os


def store_file(sock, dst, file_name):
    data_size = len(file_name.encode())
    sock.send(pack("h", data_size))
    sock.send(file_name.encode())
    directory = os.path.dirname(dst)
    file_exists = sock.recv(1)
    if file_exists == b'e':
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(dst, 'wb') as f:
            data = sock.recv(1024)
            while data:
                f.write(data)
                data = sock.recv(1024)
        print('Successfully get the file')
    elif file_exists == b'i':
        print("The file doesn't exist")


def download_file(server_address, name, dst):
    # TODO: Implementar TCP download_file client
    print('TCP: download_file({}, {}, {})'.format(server_address, name, dst))
    (server_host, server_port) = server_address
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(server_address)
        sock.send(b'd')
        store_file(sock, dst, name)
