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
            "data payload":             (0,    8191),
            "packet info":              (8192, 8193),
            "channel count":            (8194, 8195),
            "packet count":             (8196, 8199),
            "ptp timestamp":            (8200, 8211)
        }

        self.packets = None


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

        print(II[0][90:110])

        return II, QQ


# ============================================================================ #
# packetsHH
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