# ============================================================================ #
# _cfg_board.bak.py
# Board configuration file.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT/FYST 2023  
# Edited by: Shubh Agrawal shubh@sas.upenn.edu 
# for TIM 2025
# ============================================================================ #



# ============================================================================ #
# board identifier
bid = 1    # should match physical id on board


# ============================================================================ #
# logging
log_path         = '../logs/board.log'
log_MB           = 10  # size of log files
log_backup_count = 5   # number of log files
print_traceback = True  # set to True to print traceback on error
test_mode       = False # disables any firmware calls, useful for testing on local machine

# ============================================================================ #
# Firmware
firmware_file = 'init/tetra_v14p1.xsa'
asu_board = False

# ============================================================================ #
# redis server configuration
# host = '192.168.2.81'
# host = 'localhost'
host = ['192.168.1.124', '192.168.1.4', '192.168.1.3', '192.168.1.223', '192.168.1.151']  # redundant hosts
port = 6379
db   = 0
pw   = None


# ============================================================================ #
# PTP interface
ptp_interface   = "eth0"
ptp_mac_address = "02:0a:35:1d:7b:3c"
ptp_ip_address  = "192.168.10.1"


# ============================================================================ #
# timestream configuration
# UDP data ethernet destination
udp_dest_ip  = '192.168.2.80'
udp_dest_mac = '6c:1f:f7:d3:5e:4c'
# per-drone UDP destinations (override udp_dest_ip/udp_dest_mac above; unset -> shared)
# multicast group per drone (MAC = 01:00:5e + low 23 bits of the group IP)
udp_dest_ip_1  = '239.255.1.10'
udp_dest_mac_1 = '01:00:5e:7f:01:0a'
udp_dest_ip_2  = '239.255.1.11'
udp_dest_mac_2 = '01:00:5e:7f:01:0b'
udp_dest_ip_3  = '239.255.1.12'
udp_dest_mac_3 = '01:00:5e:7f:01:0c'
udp_dest_ip_4  = '239.255.1.13'
udp_dest_mac_4 = '01:00:5e:7f:01:0d'

# UDP data ethernet origin, drones 1-4
udp_ori_ip_1 = '192.168.3.50'
udp_ori_ip_2 = '192.168.3.51'
udp_ori_ip_3 = '192.168.3.52'
udp_ori_ip_4 = '192.168.3.53'
udp_ori_mac  = 'c0:ff:ee:c0:ff:ee'


# ============================================================================ #
# waveform properties
# edit with extreme caution - changes may have unitended consequences
wf_fs      = 512e6 # sample clock
wf_lut_len = 2**20 # look-up table length
wf_fft_len = 1024  # fft length
accum_len  = 2**19 - 1 # determines sample rate: wf_fs/((accum_len+1)*2)


# ============================================================================ #
# frequency sweep properties
sweep_steps    = 500 # number of sweep steps
sweep_accums   = 5   # number of repeats of each sweep (averaging)
target_chan_bw = 1 # target sweep channel bandwidth [MHz]

# ============================================================================ #
# power optimization defaults
opt_ares_min            = 4
opt_ares_max            = 300
opt_ares_cal            = 200
opt_n_iterations        = 10
opt_fine_bw             = 0.2
opt_npoints_fine        = 400
opt_N_accums            = 5
opt_fres_update_method  = 'spacing'
opt_stepdown_db         = 1
opt_qres_default        = 1e5

# ============================================================================ #
# attenuator settings
atten_device = '/dev/ttyACM0' # '/dev/ttyUSB0'
    

# ============================================================================ #
# house keeping feeds
interval_feeds = 60 # s




# ============================================================================ #
# DO NOT MODIFY BELOW
# ============================================================================ #
root_dir = ''
drone_dir = ''
temp_dir = '/tmp'
drid = 0
board_ip = '0.0.0.0'
firmware = None
# ============================================================================ #
# ============================================================================ #
