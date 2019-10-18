import os
import socket
from struct import *
import os


def store_file(connection, storage_dir):
    size_data = connection.recv(2)
    size = unpack('h', size_data)
    file_name = connection.recv(size[0])
    with open("{}/{}".format(storage_dir, file_name.decode()), 'wb') as f:
        data = connection.recv(1024)
        while data:
            f.write(data)
            data = connection.recv(1024)
    print('Successfully get the file')


def send_file(connection, storage_dir):
    size_data = connection.recv(2)
    size = unpack('h', size_data)
    file_name = connection.recv(size[0])
    if os.path.exists("{}/{}".format(storage_dir, file_name.decode())):
        # envio una e representando que existe el archivo
        connection.send(b'e')
        with open("{}/{}".format(storage_dir, file_name.decode()), 'rb') as f:
            data = f.read(1024)
            while data:
                connection.send(data)
                data = f.read(1024)
        print('Successfully sent the file')
    else:
        # envio una i representando un inexistente
        connection.send(b'i')
        print("The file doesn't exist")


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
