from datetime import datetime
import math
import os
import socket
import time

from udp_common import udp_common

CHUNK_SIZE = 25
PACKET_SIZE = CHUNK_SIZE + 1

SEQ_OFFSET = 10

class WrongSeqException(Exception):
    pass

class NoACKException(Exception):
    pass

def seq_data(seq, data):
    seq_section = bytes([seq])
    data_section = bytearray(data)
    return seq_section + data_section

def sendto_seq(sock, addr, data, seq):
    message = seq_data(seq, data)
    sock.sendto(message, addr)

def recvfrom_seq(sock, recv_size):
    recv_data, resp_addr = sock.recvfrom(recv_size)
    seq = int(recv_data[0])
    recv_content = recv_data[1:]
    return (recv_content, resp_addr, seq)

def send_with_ack(sock, addr, data, recv_size, timeout_seconds, seq, max_retries=5, expected_seq=None):
    print('{}: Sending data and expecting an ack'.format(datetime.now().strftime("%H:%M:%S.%f")))
    attempts = 0
    while attempts < max_retries:
        try:
            sendto_seq(sock, addr, data, seq)
            print('Sent data... Waiting for an ack')
            sock.settimeout(float(timeout_seconds))
            recv_data, resp_addr, resp_seq = recvfrom_seq(sock, recv_size)
            sock.settimeout(None)

            if expected_seq is None or expected_seq == resp_seq:
                return (recv_data, resp_addr)
            else:
                print("Wrong seq!!! expected {} got {}".format(expected_seq, resp_seq))
        except socket.timeout:
            print('Timeout while receiving an ack...')
        
        attempts += 1
    raise NoACKException('Did not receive an ACK after {} attempts'.format(attempts))

def recv_timeout(sock, recv_size, timeout_seconds, expected_seq=None):
    if timeout_seconds is not None:
        timeout_seconds = float(timeout_seconds)

    try:
        sock.settimeout(timeout_seconds)
        recv_data, resp_addr, resp_seq = recvfrom_seq(sock, recv_size)
        sock.settimeout(None)
        
        if expected_seq is None or expected_seq == resp_seq:
            return (recv_data, resp_addr, resp_seq)
        else:
            print("Wrong seq!!! expected {} got {}".format(expected_seq, resp_seq))

    except socket.timeout:
        print('Timeout while receiving data...')

    return (None, None, None)

def recv_with_ack(sock, data, recv_size, timeout_seconds, seq, max_retries=5, expected_seq=None):
    print('{}; Receiving data and sending an ack'.format(datetime.now().strftime("%H:%M:%S.%f")))
    attempts = 0
    if timeout_seconds is not None:
        timeout_seconds = float(timeout_seconds)
    while attempts < max_retries:
        try:
            sock.settimeout(timeout_seconds)
            recv_data, resp_addr, resp_seq = recvfrom_seq(sock, recv_size)
            sock.settimeout(None)
            if expected_seq is None or expected_seq == resp_seq:
                print('Received data... Sending an ack')
                sendto_seq(sock, resp_addr, data, seq)
                return (recv_data, resp_addr)
            else:
                print("Wrong seq!!! expected {} got {}".format(expected_seq, resp_seq))

        except socket.timeout:
            print('Timeout while receiving data...')
        
        attempts += 1
    raise RuntimeError('Did not receive an ACK after {} attempts'.format(attempts))

def receive_chunk(sock):
    file_content, resp_addr, seq = recvfrom_seq(sock, PACKET_SIZE)

    if seq < SEQ_OFFSET:
        raise WrongSeqException("receive_chunk got wrong seq")

    seq = seq - SEQ_OFFSET
    print("Got chunk {} of length {}".format(seq + 1, len(file_content)))
    print("ACK chunk {}".format(seq))
    sendto_seq(sock, resp_addr, "-".encode(), seq + SEQ_OFFSET) # ack chunk
    return seq, file_content

def receive_file(sock, server_address, dest_path, filesize):
    total_chunks = math.ceil(filesize / CHUNK_SIZE)
    chunks_not_received = list(range(0, total_chunks))
    print("Receiving file {} of size {}kB".format(dest_path, math.ceil(filesize/1024)))
    print("Need to get {} chunks".format(total_chunks))
    file_data = [None] * total_chunks
    with open(dest_path, 'wb') as f:
        while len(chunks_not_received) > 0:
            seq, file_content = receive_chunk(sock)
            file_data[seq] = file_content
            if seq in chunks_not_received:
                chunks_not_received.remove(seq)
        print('got all chunks. writing...')
        for chunk in file_data:
            f.write(chunk)
    
    # Other party may have not gotten our ACKs.
    # Reply any messages over SEQ_OFFSET with an ACK

    print('Waiting for FIN from other client')
    got_fin = False

    while not got_fin:
        file_content, server_address, seq = recv_timeout(sock, PACKET_SIZE, 5)

        if seq is None:
            print("Did not get FIN, assume client closed connection")
            break

        print("Got seq", seq)
        if seq >= SEQ_OFFSET:
            sendto_seq(sock, server_address, "-".encode(), seq) # ack chunk
        else:
            print('Got fin!')
            sendto_seq(sock, server_address, "-".encode(), 3) # ack chunk
            break

    print('Successfully got the file')

def send_chunks(sock, server_address, chunk_indexes, file_content):
    total_chunks = len(file_content)
    chunks_not_ackowledged = list(range(0, total_chunks))

    for i in chunk_indexes:
        print("Sending chunk {}/{} of length {}".format(i + 1, total_chunks, len(file_content[i])))
        sendto_seq(sock, server_address, file_content[i], i + SEQ_OFFSET) # ack chunk



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

        time.sleep(0.5)
        print("chunks_not_ackowledged", chunks_not_ackowledged)
        chunks_to_remove = []
        for c in chunks_not_ackowledged:
            print("chunks_not_ackowledged", c)
            resp, resp_addr, ack_seq = udp_common.recv_timeout(sock, 15, 1)

            if resp is None:
                # We got a timeout, send chunks again
                break
            elif ack_seq < SEQ_OFFSET:
                raise WrongSeqException("send_file got wrong seq")
            else:
                ack_seq = ack_seq - SEQ_OFFSET
                print("Got ack for {}, removing from list".format(ack_seq + 1))
                if ack_seq in chunks_not_ackowledged:
                    chunks_to_remove.append(ack_seq)
        
        for ack_seq in chunks_to_remove:
            chunks_not_ackowledged.remove(ack_seq)

    try:
        udp_common.send_with_ack(
            sock,
            server_address,
            "FIN".encode(),
            1,
            1,
            3,
            expected_seq=3
        )
    except RuntimeError:
        print("Did not get a FIN ack from other party, assume closed connection")

    print('Successfully sent the file')