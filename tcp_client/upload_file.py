import socket
from struct import *


def send_file(sock, src, file_name):
    data_size = len(file_name.encode())
    print(data_size)
    sock.send(pack("h", data_size))
    sock.send(file_name.encode())
    with open(f"{src}", 'rb') as f:
        data = f.read(1024)
        while data:
            sock.send(data)
            data = f.read(1024)
    print('Successfully sent the file')


def upload_file(server_address, src, name):
    print('TCP: upload_file({}, {}, {})'.format(server_address, src, name))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(server_address)
        sock.send(b'u')
        send_file(sock, src, name)

