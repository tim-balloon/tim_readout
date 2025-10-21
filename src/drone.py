# ============================================================================ #
# drone.py
# Board side Redis interface script.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT/FYST 2024
# Edited by: Shubh Agrawal shubh@sas.upenn.edu 
# for TIM 2025
# ============================================================================ #



# ============================================================================ #
# IMPORTS
# ============================================================================ #


import os
import sys
import time
import redis
import queue
import shutil
import pickle
import logging
import argparse
import builtins
import importlib
import threading
import logging.handlers
import socket
import struct
import numpy as np

import alcove
from config import board as cfg_b
import redis_channels as chans
import feeds




# ============================================================================ #
# MAIN
# ============================================================================ #


def main():
    # CTRL-c to exit out of listen mode

    # setup logging
    _setupLogging()

    # setup and get the CLI args
    args = _setupArgparse() 

    # modify the configs as necessary
    _modifyConfig(args)

    # setup a drone specific dir in /tmp
    _setupTmpDir()

    # load firmware to config
    _loadFirmware()

    udp_sock = _makeUDPSocket() if cfg_b.udp_send else None

    # connect to Redis server and establish connection objects
    r, p = connectRedis(set_client_name=True)

    print(f"Drone {cfg_b.bid}.{cfg_b.drid} is running...") 
    if cfg_b.test_mode:
        print("RUNNING IN TEST MODE, NO FIRMWARE LOADED OR EXECUTED!!!!!!")

    # run loop
    command_queue = queue.Queue()
    listenMode(r, p, chans.subList(cfg_b.bid, cfg_b.drid), 
               command_queue, cfg_b.interval_feeds, udp_sock)


# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# _setupLogging
def _setupLogging():

    # Create a rotating file handler
    handler = logging.handlers.RotatingFileHandler(
        cfg_b.log_path, 
        maxBytes=cfg_b.log_MB * 1024 * 1024, 
        backupCount=cfg_b.log_backup_count
    )

    # Set the logging format
    formatter = logging.Formatter(
        '{asctime} {levelname} {filename}:{lineno}: {message}',
        datefmt='%Y-%m-%d %H:%M:%S',
        style='{'
    )
    handler.setFormatter(formatter)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the logging level
    logger.addHandler(handler)


# ============================================================================ #
# _print (monkeypatch)
_print = print 
def print(*args, **kw):
    '''Override the print statement.
    '''
    
    msg = ""

    # add drone id
    if cfg_b.bid and cfg_b.drid:
        # msg += f"drone={cfg_b.bid}.{cfg_b.drid}: "
        msg += f"{cfg_b.bid}.{cfg_b.drid}: "

    # add current filename
    # msg += f"{os.path.basename(__file__)}: "

    # add print strings
    msg += " ".join(map(str, args))

    # log msg
    logging.info(msg)

    # print to console
    _print(msg, **kw)

builtins.print = print


# ============================================================================ #
# _setupArgparse
def _setupArgparse():
    '''Setup the argparse arguments'''

    parser = argparse.ArgumentParser(
        description='Terminal interface to drone script.')

    # add arguments
    parser.add_argument(                # positional, required, 1-4
        "drid", type=int, help="drone id", choices=range(1,4+1))
   
    # return arguments values
    return parser.parse_args()


# ============================================================================ #
# _modifyConfig
def _modifyConfig(args):
    '''modify config level variables'''

    # project root directory (src)
    cfg_b.src_dir = os.getcwd()          # assuming this file lives in root dir

    # parent directory
    par_dir = os.path.realpath(os.path.pardir)

    # drone directory
    cfg_b.drone_dir = f'{par_dir}/drones/drone{args.drid}'

    # tmp directory
    cfg_b.temp_dir = f'/tmp/drone{args.drid}'

    # drone config
    sys.path.append(cfg_b.drone_dir)
    cfg_dr = importlib.import_module(f'_cfg_drone{args.drid}')

    # drone identifier
    cfg_b.drid = cfg_dr.drid


# ============================================================================ #
# _setupTmpDir
def _setupTmpDir():
    '''Setup the system tmp directory to use.
    '''

    d = cfg_b.temp_dir

    # Ensure the custom directory is fresh
    if os.path.exists(d):
        shutil.rmtree(d)  # Delete the existing directory
    os.makedirs(d)        # Create a fresh directory

    # Set the TMPDIR environment variable
    os.environ["TMPDIR"] = d


# ============================================================================ #
# _loadFirmware
def _loadFirmware():

    try:
        from pynq import Overlay # type: ignore

        firmware_file = os.path.join(cfg_b.dir_root, cfg_b.firmware_file)
        cfg_b.firmware = Overlay(firmware_file, ignore_version=True, download=False)

    except Exception as e: 
        firmware = None


# ============================================================================ #
# connectRedis
def connectRedis(set_client_name=False):
    '''
    connect to redis server
    tries to iterate through all hosts in cfg_b.host
    '''
    if not type(cfg_b.host) is list:
        hosts = [cfg_b.host]  # Ensure host is a list for iteration
    else:
        hosts = cfg_b.host
    
    host_found = False
    while not host_found:
        for host in hosts:
            try:
                r = redis.Redis(host=host, port=cfg_b.port, db=cfg_b.db, password=cfg_b.pw, socket_connect_timeout=2)
                p = r.pubsub()
                r.ping()
                if set_client_name:
                    r.client_setname(f'drone_{cfg_b.bid}.{cfg_b.drid}')
                host_found = True
                print(f"Connected to Redis host: {host}")
                break  # Exit loop if connection is successful
            except redis.exceptions.ConnectionError as e:
                print(f"Failed to connect to Redis host: {host}, error: {e}")
                continue
            except redis.exceptions.TimeoutError as e:
                print(f"Redis connection timeout: {e} for host {host}")
                continue

    return r, p


# ============================================================================ #
# _loopExecuteCommands
def _loopExecuteCommands(r, command_queue, stop_event=None):
    '''Loop to listen for and sequentially execute commands.
    '''

    while stop_event is None or not stop_event.is_set():

        chan_str, payload = command_queue.get()  # Get next command from queue
        try:
            com_num, ret_data, args, kwargs = payloadToCom(payload)
            com_ret = executeCommand(com_num, ret_data, args, chan_str, kwargs)
        except Exception as e:
            com_ret = f"Payload error ({payload}): {e}"
            print(com_ret)
        
        publishResponse(com_ret, r, chan_str)  # Send response
        command_queue.task_done()


# ============================================================================ #
# _loopUpdateFeeds
def _loopUpdateFeeds(r, interval, stop_event=None, udp_sock=None):
    """Loop to update feeds.
    """

    while stop_event is None or not stop_event.is_set():
        try:
            feeds.setFeedSpc(r, interval)   # free disk space
            feeds.setFeedTemps(r, interval) # temperatures 
            
            if udp_sock is not None:
                _sendToneListUDP(udp_sock)  # UDP tone list feed
            time.sleep(interval)

        except Exception as e:
            if not cfg_b.test_mode:
                print(f"ERROR in drone.py._loopUpdateFeeds: {e}")
            time.sleep(5)  # Prevent crashing loop from overloading CPU

# Add a UDP feed for tone list if in config
def _makeUDPSocket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', cfg_b.tone_list_port))  # Bind to the port

    mreq = struct.pack("4sl", socket.inet_aton(cfg_b.tone_list_addr), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    return sock

def _sendToneListUDP(udp_sock):
    tone_list = [1, 2, 3, 4, 5]  # Example tone list; replace with actual data retrieval
    if tone_list is None:
        return
    data = np.array(tone_list, dtype=np.float32).tobytes()
    timestamp = time.time_ns()
    data = timestamp.to_bytes(8, byteorder='big') + data
    udp_sock.sendto(data, (cfg_b.tone_list_addr, cfg_b.tone_list_port))


# ============================================================================ #
# listenMode
def listenMode(r, p, chan_subs, command_queue, interval_feeds, udp_sock):
    '''
    '''

    stop_event = threading.Event() if type(cfg_b.host) is list else None
    # If multiple Redis hosts are specified, stop_event is used to signal threads to stop
    
    # Start feeds thread
    threading.Thread(
        target=_loopUpdateFeeds, args=(r,interval_feeds,stop_event,udp_sock), daemon=True
        ).start()

    # Start commands thread
    threading.Thread(
        target=_loopExecuteCommands, args=(r,command_queue,stop_event), daemon=True
        ).start()

    # Command loop: listens for messages and adds them to the queue
    while True:
        try:
            p.psubscribe(chan_subs)  # Subscribe to channels
            last_chan_str = ''
            for new_message in p.listen():
                if new_message['type'] != 'pmessage':
                    continue  # Ignore non-command messages

                chan_str = new_message['channel'].decode('utf-8')

                if chan_str == last_chan_str: # command unique
                    continue  # Prevent duplicate processing
                last_chan_str = chan_str

                payload = new_message['data'].decode('utf-8')

                # Queue the command for execution
                command_queue.put((chan_str, payload))
        except redis.exceptions.ConnectionError as e:
            if not isinstance(cfg_b.host, list):
                print(f"Redis connection error: {e}, no redundant hosts available.")
                raise e  # Raise the error
            
            stop_event.set()  # Signal threads to stop
            r, p = connectRedis(set_client_name=True)  
            # Reconnect to Redis, function does not return till new host is found
            
            print(f"Reconnected, restarting threads...")
            stop_event.clear()  # Clear the stop event to allow threads to run again
            threading.Thread(
                target=_loopUpdateFeeds, args=(r, interval_feeds, stop_event), daemon=True
                ).start()
            threading.Thread(
                target=_loopExecuteCommands, args=(r, command_queue, stop_event), daemon=True
                ).start()


'''
def listenMode(r, p, chan_subs):
    p.psubscribe(chan_subs)             # channels to listen to

    last_chan_str = ''

    for new_message in p.listen():      # infinite listening loop
        # print(new_message)

        # check this is a command
        if new_message['type'] != 'pmessage':
            continue

        # get channel string (unique to command)
        chan_str = new_message['channel'].decode('utf-8')
        # cid = chan_sub.split('_')[-1]    # recover cid from channel

        # check we haven't already processed this message
        # e.g. could have come through on another channel
        if chan_str == last_chan_str:
            continue
        last_chan_str = chan_str

        payload = new_message['data'].decode('utf-8')
        try:
            com_num, ret_data, args, kwargs = payloadToCom(payload)
            # print(com_num, args, kwargs)
            com_ret = executeCommand(com_num, ret_data, args, chan_str, kwargs)
        except Exception as e:
            com_ret = f"Payload error ({payload}): {e}"
            print(com_ret)
        
        # publishResponse(com_ret, r, bid, cid) # send response
        publishResponse(com_ret, r, chan_str) # send response
'''


# ============================================================================ #
# executeCommand
def executeCommand(com_num, ret_data, args, chan_str, kwargs):
    '''
    ret_data: (bool) Whether to return data from command func.
    '''

    print(f"Exe com {com_num} (chan: {chan_str} args={args} {kwargs})")

    # execute the command
    try:
        ret = alcove.callCom(com_num, args, kwargs)

    # command execution failed
    except Exception as e:
        ret = f"Command execution error: {e}"
        print(f" Command {com_num} execution failed.")

    # command execution successful
    else:
        if ret is None or not ret_data:
            ret = f"Command {com_num} executed." # success ack.
        # print(f" Command {com_num} execution done.")

    return ret


# ============================================================================ #
# publishResponse
def publishResponse(resp, r, chan_str):
    '''Publish a response on return channel.
    '''

    chan = chans.comChan(chan=chan_str)
    # print(f" {chan.pubRet}")

    try: 
        ret = pickle.dumps(resp) # convert to bytes object; required by Redis
        r.publish(chan.pubRet, ret) # publish resp with Redis on return channel

    except Exception as e:
        print(f' Publish response failed with error: {e}')
    else:
        # print(f' Publish response successful.')
        pass


# ============================================================================ #
# listToArgsAndKwargs
def listToArgsAndKwargs(args_list):
    """Split an arg list into args and kwargs.
    l: Args list to split.
    Returns args (list) and kwargs (dictionary)."""
    
    args_str = ' '.join(args_list)
    args_str = args_str.replace(",", " ")
    args_str = args_str.replace("=", " = ")
    args_str = ' '.join(args_str.split()) # remove excess whitespace
    l = args_str.split()
    
    args = []
    kwargs = {}
    while len(l)>0:
        v = l.pop(0)

        if len(l)>0 and l[0]=='=': # kwarg
            l.pop(0) # get rid of =
            kwargs[v] = l.pop(0)

        else: # arg
            args.append(v)

    return args, kwargs


# ============================================================================ #
# payloadToCom
def payloadToCom(payload):
    """
    Convert payload to com_num, args, kwargs.
        payload: Command string data.
            Payload format: [com_num] [positional arguments] [named arguments].
            Named arguments format: -[argument name] [value].
    """
    
    paylist = payload.split()
    com_num = int(paylist.pop(0)) # assuming first item is com_num
    ret_data = int(paylist.pop(0)) # assuming second item is ret_data
    args, kwargs = listToArgsAndKwargs(paylist)
    
    return com_num, ret_data, args, kwargs


# ============================================================================ #
# get/setKeyValue
def getKeyValue(key):
    """
    GET the value of given key.
    """

    r,p = connectRedis()
    ret = r.get(bytes(key, encoding='utf-8'))
    ret = None if ret is None else ret.decode('utf-8')

    return ret

def setKeyValue(key, value):
    """
    SET the given value for the given key.
    """

    r,p = connectRedis()
    r.set(bytes(key, encoding='utf-8'), bytes(value, encoding='utf-8'))   



# ============================================================================ #
# MAIN
# ============================================================================ #


if __name__ == "__main__":
    main()