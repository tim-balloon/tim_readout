import os, json, time, traceback
import numpy as np
import rfsockid
from rfsockid.procedures import optimize_ares_siq
from alcove_commands.alcove_base import *
from base_io import _timestamp
import alcove_commands.tones as tones
from alcove_commands.local_backend import LocalRFSOC

def optimizePower(
        ares_min=None,
        ares_max=None,
        ares_cal=None,
        n_iterations=None,
        fine_bw=None,
        npoints_fine=None,
        N_accums=None,
        fres_update_method=None,
        stepdown_db=None,
):
    def _arg(val, default, cast):
        # arguments from command will arrive as strings;
        # type cast them to different types
        try:
            return cast(val)
        except:
            return default

    # type cast
    ares_min        = _arg(ares_min,        cfg_b.opt_ares_min,     float)
    ares_max        = _arg(ares_max,        cfg_b.opt_ares_max,     float)
    ares_cal        = _arg(ares_cal,        cfg_b.opt_ares_cal,     float)
    n_iterations    = _arg(n_iterations,    cfg_b.opt_n_iterations, int)
    fine_bw         = _arg(fine_bw,         cfg_b.opt_fine_bw,      float)
    npoints_fine    = _arg(npoints_fine,    cfg_b.opt_npoints_fine, int)
    N_accums        = _arg(N_accums,        cfg_b.opt_N_accums,     int)
    fres_update_method = _arg(fres_update_method, cfg_b.opt_fres_update_method, str)
    stepdown_db     = _arg(stepdown_db,     cfg_b.opt_stepdown_db,  float)

    # load fres, qres, fcal_indices
    try:
        fres = io.load(io.file.f_res_targ)
    except FileNotFoundError:
        raise FileNotFoundError("fres file does not exists. Write resonance frequencies first.")

    try:
        qres = io.load(io.file.q_res_targ)
    except Exception:
        qres = np.full(len(fres), fill_value=cfg_b.opt_qres_default)

    try:
        fcal_indices = io.load(io.file.f_cal_indices_targ)
    except Exception:
        fcal_indices = np.array([], dtype=int)

    # check array sizes
    if len(fres) != len(qres):
        raise ValueError(f"Size of fres ({len(fres)}) and qres ({len(qres)}) should match.")

    # set up job
    job_id = _timestamp()
    job_dir = f"{cfg_b.drone_dir}/optPower/{job_id}"
    backend = LocalRFSOC(job_id=job_id, job_dir=job_dir)    # RFSoC backend
    if backend.r is not None:
        backend.r.delete(backend.abort_key)
    backend.progress("starting", frac=0)

    # run optimizer
    t_start = time.time()
    state, err, res = "error", None, None
    try:
        res = optimize_ares_siq(
            backend=backend,
            fres=fres,
            ares_min=ares_min,
            ares_max=ares_max,
            ares_cal=ares_cal,
            qres=qres,
            fcal_indices=fcal_indices,
            n_iterations=n_iterations,
            fine_bw=fine_bw,
            fres_update_method=fres_update_method,
            npoints_fine=npoints_fine,
            N_accums=N_accums,
            stepdown_db=stepdown_db,
        )
        state = "aborted" if res["aborted"] else "done"
    except Exception:
        err = traceback.format_exc();
        print(err)

    # write final comb
    if state == "done":
        try:
            tones.writeCombArrays(res["fres"], res["ares"])
        except Exception:
            comb_err = traceback.format_exc();
            print(comb_err)
            err = (err or "") + comb_err
    else:
        # fall back
        f_safe = res["fres"] if res is not None else io.load(io.file.f_res_targ)
        a_safe = np.full(len(f_safe), ares_min)
        a_safe[fcal_indices] = ares_cal
        tones.writeCombArrays(f_safe, a_safe)

    # info
    info = {
        "job_id"    : job_id,
        "state"     : state if err is None else "error: " + err.strip().splitlines()[-1],
        "n_done"    : res["n_done"] if res else 0,
        "t_start"   : t_start,
        "t_end"     : time.time(),
        "rfsockid_version": rfsockid.__version__,
    }

    backend.save("summary", np.array(info, dtype=object))
    if backend.r is not None:
        backend.r.set(backend.job_key, json.dumps(info), ex=86400)

    if res is None:
        return io.returnWrapper({"fname": "optpow_info", "file_type": "npy"}, info)
    return io.returnWrapperMultiple(
        [{"fname": fname, "file_type": "npy"} for fname in 
          ("optpow_fres", "optpow_ares", "optpow_state_history", "optpow_ares_history", "optpow_info")],
        [res["fres"], res["ares"], res["state_history"], res["ares_history"], info]
          
    )

def fetchJobData(job_id=None, names=None):
    """
    Sends the data to computer.
    names: summary, fres_opt, ares_opt, time_prof, fres_XX, ares_XX, s21_fine_XX
    """

    if job_id is None:
        # use the newest folder
        job_id = sorted(os.listdir(f'{cfg_b.drone_dir}/optPower'))[-1]
    job_dir = os.path.join(f'{cfg_b.drone_dir}/optPower', job_id)

    if not os.path.isdir(job_dir):
        raise FileNotFoundError(f"no job folder {job_dir}")

    DELIM = ';'
    data_list = []
    fname_list = []

    if (names == "all") or (names is None):
        for fname in os.listdir(job_dir):
            if fname.startswith('s21'):
                continue
            if not fname.endswith('.npy'):
                continue

            fname_list.append(os.path.splitext(fname)[0])
        
    else:
        fname_list = [name.strip() for name in names.split(DELIM) if name.strip()]

    for fname in fname_list:
        fpath = os.path.join(job_dir, fname+'.npy')
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"{fname}.npy not found in {job_dir}")
        data = np.load(os.path.join(job_dir, fname+'.npy'), allow_pickle=True)
        data_list.append(data)

    return io.returnWrapperMultiple(
        [{"fname": "optpow_"+fname, "file_type": "npy"} for fname in fname_list],
        data_list
    )


    