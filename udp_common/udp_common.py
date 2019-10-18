from datetime import datetime
import math
import os
import socket

CHUNK_SIZE = 25
PACKET_SIZE = CHUNK_SIZE + 1

def send_with_ack(sock, addr, data, recv_size, timeout_seconds, max_retries=5):
    print('{}: Sending data and expecting an ack'.format(datetime.now().strftime("%H:%M:%S.%f")))
    attempts = 0
    while attempts < max_retries:
        try:
            sock.sendto(data, addr)
            print('Sent data... Waiting for an ack')
            sock.settimeout(float(timeout_seconds))
            recv_data, resp_addr = sock.recvfrom(recv_size)
            sock.settimeout(None)
            return (recv_data, resp_addr)
        except socket.timeout:
            print('Timeout while receiving an ack...')
            attempts += 1
    raise RuntimeError('Did not receive an ACK after {} attempts'.format(attempts))

def recv_with_ack(sock, data, recv_size, timeout_seconds, max_retries=5):
    print('{}; Receiving data and sending an ack'.format(datetime.now().strftime("%H:%M:%S.%f")))
    attempts = 0
    while attempts < max_retries:
        try:
            sock.settimeout(float(timeout_seconds))
            recv_data, resp_addr = sock.recvfrom(recv_size)
            sock.settimeout(None)
            print('Received data... Sending an ack')
            sock.sendto(data, resp_addr)
            return (recv_data, resp_addr)
        except socket.timeout:
            print('Timeout while receiving data...')
            attempts += 1
    raise RuntimeError('Did not receive an ACK after {} attempts'.format(attempts))

def receive_file(sock, server_address, dest_path, filesize):
    total_chunks = math.ceil(filesize / CHUNK_SIZE)
    chunks_received = 0
    print("Receiving file {} of size {}kB".format(dest_path, math.ceil(filesize/1024)))
    print("Need to get {} chunks".format(total_chunks))
    with open(dest_path, 'wb') as f:
        while chunks_received != total_chunks:
            data = sock.recv(PACKET_SIZE)
            chunks_received += 1
            seq = int(data[0])
            file_content = data[1:]
            print("Got chunk {}/{} of length {}".format(chunks_received, total_chunks, len(file_content)))
            f.write(file_content)
    print('Successfully got the file')


def send_file(sock, server_address, file_path):
    filesize = os.path.getsize(file_path)
    total_chunks = math.ceil(filesize / CHUNK_SIZE)
    chunks_sent = 0
    print("Sending file {} of size {}kB".format(file_path, math.ceil(filesize/1024)))
    print("Need to send {} chunks".format(total_chunks))
    with open(file_path, 'rb') as f:
        data = f.read(CHUNK_SIZE)
        while data:
            seq_section = bytes([chunks_sent])
            data_section = bytearray(data)
            packet_data = seq_section + data_section
            print("Sending chunk {}/{} of length {}".format(chunks_sent + 1, total_chunks, len(data_section)))
            sock.sendto(packet_data, server_address)
            chunks_sent += 1
            data = f.read(25)
    print('Successfully sent the file')