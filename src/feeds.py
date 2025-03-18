# ============================================================================ #
# feeds.py
# Drone feed functions.
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2025
# ============================================================================ #

import shutil

import alcove_commands.board_utilities as utils
from config import board as cfg_b




# ============================================================================ #
# _wilds
def _wilds():
    """Feed wild cards.
    """

    wilds = {
        'temp' : f'temp:*',
        'spc'  : f'spc:*',
    }

    return wilds


# ============================================================================ #
# _keys
def _keys():
    """Feed keys.
    """

    id = f'{cfg_b.bid}.{cfg_b.drid}'

    keys = {
        'temp_ps' : f'temp:{id}:ps', # e.g. 'temp:1.1:ps'
        'temp_pl' : f'temp:{id}:pl', # e.g. 'temp:1.1:pl'
        'spc'     : f'spc:{id}',     # e.g. 'spc:1.1'
    }

    return keys


# ============================================================================ #
# _getKeyValsMatching
def _getKeyValsMatching(r, match):
    """
    """

    result = {}
    cursor = 0
    while True:

        # get batch of data
        # use SCAN to scale efficiently
        cursor, keys = r.scan(cursor=cursor, match=match)
        for key in keys:
            result[key.decode()] = r.get(key).decode() 

        # Exit loop when all data collected
        if cursor == 0:
            break

    return result


# ============================================================================ #
# _setKeyVal
def _setKeyVal(r, key, val, expire=None):
    """Set a val for a key, with optional expiry, in s.
    """

    r.set(key, val)

    if expire is not None:
        r.expire(key, expire)


# ============================================================================ #
# getFeedTemps
def getFeedTemps(r, handler):
    """Get all drones feeds: Temperatures (pl and ps), in celsius.

    ps = processing system
    pl = programmable logic
    """

    keyvals = _getKeyValsMatching(r, _wilds()['temp'])
    handler('drone_temperatures_C', keyvals)
    
    # data = {}
    # for key in keyvals:
    #     _,id,sensor = key.split(':') 
    #     temp = keyvals[key]
    #     data[f"{id}:{sensor}"] = temp

    
# ============================================================================ #
# getFeedSpc
def getFeedSpc(r, handler):
    """Get all drones feeds: Free space remaining, in GB.
    """

    keyvals = _getKeyValsMatching(r, _wilds()['spc'])
    handler('drone_free_spaces_GB', keyvals)


# ============================================================================ #
# setFeedTemps
def setFeedTemps(r, interval):
    """Update the ps and pl temperature feeds.
    """

    temps = utils.board_temps()
    temp_ps = temps['ps_processor']
    temp_pl = temps['pl_fabric']

    _setKeyVal(r, _keys()['temp_ps'], temp_ps, 2*interval)
    _setKeyVal(r, _keys()['temp_pl'], temp_pl, 2*interval)


# ============================================================================ #
# setFeedSpc
def setFeedSpc(r, interval):
    """Update the free disk space feed.
    """

    total, used, free = shutil.disk_usage("/") # bytes
    free = round(free / (1024 ** 3), 4) # GB, round to 4 digits

    _setKeyVal(r, _keys()['spc'], free, 2*interval)