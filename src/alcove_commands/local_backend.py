import os, json, time
import numpy as np
import redis
from rfsockid.backend import ReadoutBackend
from alcove_commands.alcove_base import *
import alcove_commands.tones as tones
import alcove_commands.sweeps as sweeps

class LocalRFSOC(ReadoutBackend):
    def __init__(self, job_dir, job_id):
        self.job_dir = job_dir
        self.job_id = job_id
        self.chan = cfg_b.drid
        self.job_key = f"job_{cfg_b.bid}.{cfg_b.drid}"
        self.abort_key = f"abort_{cfg_b.bid}.{cfg_b.drid}"
        self.phis = None
        self.order = None
        r, p = self.connectRedis()
        self.r = r
        self.p = p

    def connectRedis(self):
        '''
        connect to redis server
        tries to iterate through all hosts in cfg_b.host
        '''
        if not type(cfg_b.host) is list:
            hosts = [cfg_b.host]  # Ensure host is a list for iteration
        else:
            hosts = cfg_b.host
        
        r = None
        p = None
        for host in hosts:
            try:
                r = redis.Redis(host=host, port=cfg_b.port, db=cfg_b.db, password=cfg_b.pw, socket_connect_timeout=2)
                p = r.pubsub()
                r.ping()
                print(f"Connected to Redis host: {host}")
                break  # Exit loop if connection is successful
            except redis.exceptions.RedisError as e:
                print(f"Failed to connect to Redis host: {host}, error: {e}")
                r = None

        return r, p

    def write_comb(self, fres, ares):
        self.order = np.argsort(fres)   # sweeps._sweep internally sorts fres; need this to reorder the data into the original order
        f_rf_actual, amps, phis = tones.writeCombArrays(fres[self.order], ares[self.order])
        self.f_rf_sorted = f_rf_actual
        self.phis = phis

        if len(np.unique(f_rf_actual)) != len(fres):
            raise ValueError("fres has duplicate frequencies.")

    def target_sweep(self, npoints, bandwidth, N_accums):
        f_center = io.load(io.file.f_center_vna)    # Hz
        f, Z = sweeps._sweep(self.chan,
                             f_center/1e6,
                             self.f_rf_sorted - f_center,
                             npoints, chan_bandwidth=bandwidth, N_accums=N_accums)

        # reorder data
        f = f.reshape(-1, npoints)
        Z = Z.reshape(-1, npoints)
        inv = np.argsort(self.order)
        return f[inv].ravel(), Z[inv].ravel()

    def save(self, name, arr):
        os.makedirs(self.job_dir, exist_ok=True)
        np.save(os.path.join(self.job_dir, name), arr)

    def progress(self, msg=None, frac=None, **info):
        if self.r is None:
            print("WARNING: no Redis connection; progress report disabled")
            return
        try:
            self.r.set(self.job_key,
                    json.dumps({
                        "job_id": self.job_id,
                        "state": "running",
                        "msg": msg,
                        "frac": frac,
                        "t": time.time(),
                        **info
                    }),
                    ex=86400)
            print(msg)
        except Exception as e:
            print(f"progress: {type(e).__name__}: {e}")
        

    def should_abort(self):
        if self.r is None:
            print("WARNING: no Redis connection; abort disabled")
            return False
        try:
            if self.r.get(self.abort_key) in [None, b"", b"0"]:
                return False
            else:
                return True
        except Exception:
            return False