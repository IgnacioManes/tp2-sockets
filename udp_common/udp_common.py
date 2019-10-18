from datetime import datetime
import math
import os
import socket
import time

from udp_common import udp_common

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

def recv_timeout(sock, recv_size, timeout_seconds):
    if timeout_seconds is not None:
        timeout_seconds = float(timeout_seconds)

    try:
        sock.settimeout(timeout_seconds)
        recv_data, resp_addr = sock.recvfrom(recv_size)
        sock.settimeout(None)
        return (recv_data, resp_addr)
    except socket.timeout:
        print('Timeout while receiving data...')

    return (None, None)

def recv_with_ack(sock, data, recv_size, timeout_seconds, max_retries=5):
    print('{}; Receiving data and sending an ack'.format(datetime.now().strftime("%H:%M:%S.%f")))
    attempts = 0
    if timeout_seconds is not None:
        timeout_seconds = float(timeout_seconds)
    while attempts < max_retries:
        try:
            sock.settimeout(timeout_seconds)
            recv_data, resp_addr = sock.recvfrom(recv_size)
            sock.settimeout(None)
            print('Received data... Sending an ack')
            sock.sendto(data, resp_addr)
            return (recv_data, resp_addr)
        except socket.timeout:
            print('Timeout while receiving data...')
            attempts += 1
    raise RuntimeError('Did not receive an ACK after {} attempts'.format(attempts))

def receive_chunk(sock):
    data, addr = sock.recvfrom(PACKET_SIZE)
    seq = int(data[0])
    file_content = data[1:]
    print("Got chunk {} of length {}".format(seq + 1, len(file_content)))
    print("ACK chunk {}".format(seq))
    sock.sendto(bytes(str(seq), 'utf8'), addr) # ack chunk
    return seq, file_content

def receive_file(sock, server_address, dest_path, filesize):
    total_chunks = math.ceil(filesize / CHUNK_SIZE)
    chunks_received = 0
    print("Receiving file {} of size {}kB".format(dest_path, math.ceil(filesize/1024)))
    print("Need to get {} chunks".format(total_chunks))
    file_data = [None] * total_chunks
    with open(dest_path, 'wb') as f:
        while chunks_received < total_chunks:
            seq, file_content = receive_chunk(sock)
            file_data[seq] = file_content
            chunks_received += 1
        print('got all chunks. writing...')
        for chunk in file_data:
            f.write(chunk)

    print('Successfully got the file')

def send_chunks(sock, server_address, chunk_indexes, file_content):
    total_chunks = len(file_content)
    chunks_not_ackowledged = list(range(0, total_chunks))

    for i in chunk_indexes:
        seq_section = bytes([i])
        data_section = bytearray(file_content[i])
        packet_data = seq_section + data_section
        print("Sending chunk {}/{} of length {}".format(i + 1, total_chunks, len(data_section)))
        sock.sendto(packet_data, server_address)



def send_file(sock, server_address, file_path):
    filesize = os.path.getsize(file_path)
    total_chunks = math.ceil(filesize / CHUNK_SIZE)
    chunks_sent = 0
    chunks_not_ackowledged = list(range(0, total_chunks))
    print("Sending file {} of size {}kB".format(file_path, math.ceil(filesize/1024)))
    print("Need to send {} chunks".format(total_chunks))
    file_content = []
    with open(file_path, 'rb') as f:
        data = f.read(CHUNK_SIZE)
        while data:
            file_content.append(data)
            data = f.read(25)
    print("len", len(chunks_not_ackowledged))
    while len(chunks_not_ackowledged) > 0:
        print("chunks_not_ackowledged", chunks_not_ackowledged)
        send_chunks(sock, server_address, chunks_not_ackowledged, file_content)

        time.sleep(3)
        print("chunks_not_ackowledged", chunks_not_ackowledged)
        chunks_to_remove = []
        for c in chunks_not_ackowledged:
            print("chunks_not_ackowledged", c)
            resp, resp_addr = udp_common.recv_timeout(sock, 15, 10)

            if resp is None:
                # We got a timeout, send chunks again
                break
            else:
                ack_seq = int(str(resp, 'utf8'))
                print("Got ack for {}, removing from list".format(ack_seq + 1))
                if ack_seq in chunks_not_ackowledged:
                    chunks_to_remove.append(ack_seq)
        
        for ack_seq in chunks_to_remove:
            chunks_not_ackowledged.remove(ack_seq)

    print('Successfully sent the file')