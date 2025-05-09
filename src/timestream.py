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
        self.addresses = None


# ============================================================================ #
# capturePackets
    def capturePackets(self, N):
        """
        """

        buffer_size = 9000
        rcv = [self.sock.recvfrom(buffer_size) for _ in range(N)]
        self.packets = np.array([bytearray(data) for data,_ in rcv])
        self.addresses = np.array([addr[0] for _,addr in rcv])

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
            p[i:f+1] # unconverted as each is different, so return bytes
            for p in self.packets])

        return HH
    

    def packetsIP(self):
        """IP (sender) array from packets.
        """

        if self.addresses is None:
            print(f"Error: Capture some packets first!")
            return None
        
        return self.addresses


# ============================================================================ #
# __del__
    def __del__(self):
        self.sock.close()



# ============================================================================ #
# parsePtpTimestamp

def parsePtpTimestamp(b, offset=0):

    d = np.array([b[:4], b[4:8], b[8:]])

    timestamp = int((d[-3] << 18) | (d[-2] >> 14)) + int((((d[-2] & 0x00003FFF) << 16) | (d[-1] >> 16))) * 1e-9 + offset

    return timestamp


# def parsePtpTimestamp(b, offset=0):
#     seconds = int.from_bytes(b[:6], byteorder='big')
#     nanoseconds = int.from_bytes(b[6:10], byteorder='big')
#     return seconds + nanoseconds*1e-9 + offset


# def parsePtpTimestamp(b: bytes, offset=0) -> float:
#     """Parse a 12-byte PTP timestamp into a float timestamp (seconds + nanoseconds).
#     """

#     if len(b) != 12:
#         raise ValueError("Input must be exactly 12 bytes.")

#     # Interpret the 12 bytes as a single 96-bit integer (big-endian)
#     full = int.from_bytes(b, byteorder='big')

#     # Extract bit fields
#     seconds = (full >> 48) & ((1 << 48) - 1)           # top 48 bits
#     # nanoseconds = (full >> 16) & 0x3FFFFFFF            # next 30 bits
#     nanoseconds = (full >> 16) & 0xFFFFFFFF
    
    # return seconds + nanoseconds * 1e-9 + offset


# def parsePtpTimestamp(b):
#     seconds = int.from_bytes(b[:6], byteorder='big')
#     fractional = int.from_bytes(b[6:], byteorder='big') / (1 << 48)
#     return seconds + fractional