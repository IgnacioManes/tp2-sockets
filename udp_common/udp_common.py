from datetime import datetime
import math
import os
import socket
import time

from udp_common import udp_common

# A file is split into chunks of size CHUNK_SIZE
CHUNK_SIZE = 1024
SEQ_SIZE = 4

# One byte is used to specify the sequence number
PACKET_SIZE = CHUNK_SIZE + SEQ_SIZE

# Sequence numbers are offset by this constant
# to reserve space for special handshake ones
SEQ_OFFSET = 10

# Sequence number to specify that we wish to
# close the connection
FIN_SEQ = 4

class WrongSeqException(Exception):
    pass

class NoACKException(Exception):
    pass

# Given a sequence number and a data byte array,
# create a new byte array that has the sequence number prepended
def seq_data(seq, data):
    seq_section = seq.to_bytes(SEQ_SIZE, byteorder="little")
    data_section = bytearray(data)
    return seq_section + data_section

# send a packet with a sequence number
def sendto_seq(sock, addr, data, seq):
    message = seq_data(seq, data)
    sock.sendto(message, addr)

# receive a packet with its sequence number
def recvfrom_seq(sock, recv_size):
    recv_data, resp_addr = sock.recvfrom(recv_size)
    seq = int.from_bytes(recv_data[0:SEQ_SIZE], byteorder="little")
    recv_content = recv_data[SEQ_SIZE:]
    return (recv_content, resp_addr, seq)

# send a packet and wait timeout_seconds for an ACK as a response,
# trying up to max_retries. Raise an exception if this isn't  done
# If the response has a seq that is not expected_seq, also throw
# an exception
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

# Receive a packet from the network, waiting timeout_seconds for it
# and don't retry. If a packet isn't read or if it has a seq that is not
# expected_seq, return None
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

# Receive a packet, wait timeout_seconds for it,
# trying up to max_retries. Raise an exception if this isn't  done
# Afterwards, send an ACK.
# If the received packet has a seq that is not expected_seq, also throw
# an exception
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

# Read a chunk from the network and return its file sequence and contents
def receive_chunk(sock):
    file_content, resp_addr, seq = recvfrom_seq(sock, PACKET_SIZE)

    if seq < SEQ_OFFSET:
        raise WrongSeqException("receive_chunk got wrong seq")

    file_seq = seq - SEQ_OFFSET
    print("Got chunk {} of length {}".format(file_seq + 1, len(file_content)))
    sendto_seq(sock, resp_addr, "-".encode(), seq) # ack chunk
    return file_seq, file_content

# Receive a whole file from the network in chunks.
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
            # This is an ACK that the other party did not receive
            # Send the special FIN seq number.
            sendto_seq(sock, server_address, "-".encode(), FIN_SEQ) # ack chunk
        else:
            print('Got fin!')
            got_fin = True
            sendto_seq(sock, server_address, "-".encode(), FIN_SEQ) # ack chunk
            break

    print('Successfully got the file')


# Send a list of chunks over the network
def send_chunks(sock, server_address, chunk_indexes, file_content):
    total_chunks = len(file_content)
    chunks_not_ackowledged = list(range(0, total_chunks))

    for i in chunk_indexes:
        print("Sending chunk {}/{} of length {}".format(i + 1, total_chunks, len(file_content[i])))
        sendto_seq(sock, server_address, file_content[i], i + SEQ_OFFSET) # ack chunk


# Send a whole file over the network in chunks.
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
            data = f.read(CHUNK_SIZE)
    print("len", len(chunks_not_ackowledged))
    while len(chunks_not_ackowledged) > 0:
        print("chunks_not_ackowledged", chunks_not_ackowledged)
        send_chunks(sock, server_address, chunks_not_ackowledged, file_content)

        time.sleep(1)
        print("chunks_not_ackowledged", chunks_not_ackowledged)
        chunks_to_remove = []
        for c in chunks_not_ackowledged:
            print("chunks_not_ackowledged", c)
            resp, resp_addr, ack_seq = udp_common.recv_timeout(sock, 15, 1)

            if resp is None:
                # We got a timeout, send chunks again
                break
            elif ack_seq == FIN_SEQ:
                # The other party has received all of our chunks.
                # Dont send more.
                print("The other party has received all of our chunks")
                chunks_not_ackowledged = []
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
            FIN_SEQ,
            expected_seq=FIN_SEQ
        )
    except udp_common.udp_common.NoACKException:
        print("Did not get a FIN ack from other party, assume closed connection")

    print('Successfully sent the file')