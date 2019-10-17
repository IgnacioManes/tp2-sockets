import os
import socket
from struct import *
import os


def store_file(connection, storage_dir):
    size_data = connection.recv(2)
    size = unpack('h', size_data)
    print(size[0])
    file_name = connection.recv(size[0])
    print("{}".format(file_name))
    with open("{}/{}".format(storage_dir, file_name.decode()), 'wb') as f:
        while True:
            data = connection.recv(1024)
            if data:
                f.write(data)
            else:
                print('No more data recv')
                break
    print('Successfully get the file')


def send_file(connection, storage_dir):
    size_data = connection.recv(2)
    size = unpack('h', size_data)
    print(size[0])
    file_name = connection.recv(size[0])
    with open("{}/{}".format(storage_dir, file_name.decode()), 'rb') as f:
        data = f.read(1024)
        while data:
            connection.send(data)
            data = f.read(1024)
    print('Successfully sent the file')


def start_server(server_address, storage_dir):
    print(os.getcwd())
    print('TCP: start_server({}, {})'.format(server_address, storage_dir))
    close_connections = False
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
    (server_host, server_port) = server_address
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((server_host, server_port))
        sock.listen()
        while not close_connections:
            print('waiting for a connection')
            connection, client_address = sock.accept()
            try:
                print('client connected:', client_address)
                client_action = connection.recv(1)
                if client_action == b'u':
                    store_file(connection, storage_dir)
                elif client_action == b'd':
                    send_file(connection, storage_dir)
            except Exception as e:
                print("Internal Error data")
            finally:
                print('connection closed')
                connection.close()
