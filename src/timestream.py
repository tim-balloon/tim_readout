# ============================================================================ #
# timestream.py
# Detector UDP timestream functionality.
# James Burgoyne jburgoyne@phas.ubc.ca 
# Adrian Sinclair aksincla@asu.edu
# CCAT Prime 2025  
# ============================================================================ #

import socket
import numpy as np


# ============================================================================ #
# TimeStream class
# ============================================================================ #
class TimeStream:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))

        self.packet_struct = {
            'mac destination':          (0,    5),
            'mac source':               (6,    11),
            'eth type':                 (12,   13),
            'header length':            (14,   14),
            'congestion notification':  (15,   15),
            'total length':             (16,   17),
            'Identification':           (18,   19),
            'fragment offset':          (20,   21),
            'time to live':             (22,   22),
            'protocol':                 (23,   23),
            'header checksum':          (24,   25),
            'IP source':                (26,   29),
            'IP destination':           (30,   33),
            'source port':              (34,   35),
            'destination port':         (36,   37),
            'data payload length':      (38,   39),
            'data payload checksum':    (40,   41),
            'data payload':             (42,   8233),
            'packet info':              (8234, 8235),
            'channel count':            (8236, 8237),
            'packet count':             (8238, 8241),
            'ptp timestamp':            (8242, 8253)
        }

        self.packets = None


    '''
# ============================================================================ #
# capturePacket
    def capturePacket(self, buffer_size=9000):
        message, address = self.sock.recvfrom(buffer_size)
        return bytearray(message)
        # return message.decode(), address


# ============================================================================ #
# captureNpackets
    def capturePackets(self, N):
        buffer_size = 9000
        return np.array([self.capturePacket(buffer_size) for _ in range(N)])
    

# ============================================================================ #
# convertPackets
    def convertPackets(self, packets):
        return np.array([
            np.frombuffer(p, dtype="<i").astype("float")
            for p in packets])
    

# ============================================================================ #
# getTimeStreamChunk
    def getTimeStreamChunk(self, N):
        """Grab a chunk of N packets from the timestream.
        Returns I and Q.
        """

        x = self.captureNpackets(N)
        x = self.convertPackets(x)

        I, Q = x[:,0::2].T, x[:,1::2].T

        # max number of useable channels
        I = I[:1022]
        Q = Q[:1022]
        
        return I, Q
    '''

# ============================================================================ #
# capturePackets
    def capturePackets(self, N):
        """
        """

        buffer_size = 9000

        self.packets = np.array([
            bytearray(self.sock.recvfrom(buffer_size)[0]) # (message, address)
            for _ in range(N)])

        return True
    

# ============================================================================ #
# packetsIIQQ
    def packetsIIQQ(self):
        """II and QQ 2D arrays from packets.
        II/QQ consist of 1024 I or Q tods.
        """

        if self.packets is None:
            print(f"Error: Capture some packets first!")
            return None
        
        i, f = self.packet_struct['data payload'] # initial and final bytes
        IIQQ = [
            np.frombuffer(p[i:f+1], dtype="<i4").astype("float") 
            for p in self.packets]

        II = np.array([p[0::2] for p in IIQQ]) # 1024 I tods
        QQ = np.array([p[1::2] for p in IIQQ]) # 1024 Q tods

        return II, QQ


# ============================================================================ #
# capturePackets
    def packetsHH(self, field_name):
        """HH array from packets.
        HH is tod where each 'value' is a byte array of header field data.
        """

        if self.packets is None:
            print(f"Error: Capture some packets first!")
            return None
        
        if field_name not in self.packet_struct:
            print(f"Error: Header field '{field_name}' not found.")
            return None

        i, f = self.packet_struct[field_name] # initial and final bytes
        HH = np.array([
            p[i:f+1] # should we convert?
            for p in self.packets])

        return HH


# ============================================================================ #
# __del__
    def __del__(self):
        self.sock.close()