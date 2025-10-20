#!/usr/bin/env python3
"""
runAllClientX.py

Reads the 50 client_ids listed in the comment at the end of EliteX.py
and runs EliteX.py sequentially for each client.
"""

import re
import time
import math
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Import EliteX main function
sys.path.append(str(Path(__file__).parent))
from EliteX import main as elitex_main

ROOT = Path(__file__).parent


CLIENT_IDS = [
    '10GLPHG', '10GRRXX', '10PKFPQ', '10QAXPK', '10QHKPA', '10QHLHP', '10QXGLF', '10QXRPX', '10RXAKP', '10XQKRF',
    '11AAPGR', '11ALFPK', '11FKLLH', '11FQLKK', '11FXHLQ', '11HXFGR', '11HXPLF', '11KPGQK', '11KQKXL', '11KQXAQ',
    '11LPKHH', '11QHRKF', '11QPPQG', '12AHQHL', '12APFQL', '12HAHQH', '12HAKFG', '12HHXGA', '12KRAPA', '12LFGLA',
    '12QQAHQ', '12XFGRP', '13HHAAX', '13KFXRF', '13KHGPQ', '13RXRXF', '14FPRPR', '14HFQAR', '14HPHKR', '14HPPQL',
    '14KAKGL', '14LHGPG', '14LRHXX', '14LXHLQ', '14QPXFK', '15GGGKP', '15GGRAH', '15GRGFK', '15GXHXR', '15HGRQA'
]



def _run_one(cid: str, retries: int = 2, backoff_base: int = 15) -> dict:
    t0 = time.time()
    attempt = 0
    last_err = None
    
    while attempt <= retries:
        try:
            # Call EliteX main function directly with client_id
            elitex_main(client_id=cid)
            duration = time.time() - t0
            return {"client": cid, "status": "SUCCESS", "duration": duration, "log": None, "tail": None}
            
        except Exception as e:
            last_err = e
            error_msg = str(e).lower()
            
            # Check for rate limit signals
            if "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg:
                if attempt < retries:
                    sleep_s = backoff_base * (2 ** attempt)
                    print(f"[retry] {cid} rate limit detected, retrying in {sleep_s}s (attempt {attempt+1}/{retries})", flush=True)
                    time.sleep(sleep_s)
                    attempt += 1
                    continue
            
            # Other errors - break and return failure
            duration = time.time() - t0
            return {"client": cid, "status": f"ERROR ({last_err})", "duration": duration, "log": None, "tail": [str(last_err)]}
    
    # If we get here, all retries failed
    duration = time.time() - t0
    return {"client": cid, "status": f"ERROR ({last_err})", "duration": duration, "log": None, "tail": [str(last_err)]}


def run_for_clients(client_ids: list[str], max_workers: int = 2, stagger: float = 3.0, retries: int = 2):
    total = len(client_ids)
    print(f"Total clients to run: {total}", flush=True)
    results = []
    start = time.time()
    def progress_line(done_count: int, durations: list[float]) -> str:
        bar_len = 30
        filled = int((done_count / total) * bar_len) if total else 0
        bar = "#" * filled + "." * (bar_len - filled)
        pct = int((done_count / total) * 100) if total else 100
        avg = (sum(durations) / len(durations)) if durations else 0
        eta_sec = max(0, (total - done_count) * avg)
        eta_min = int(eta_sec // 60)
        eta_s = int(eta_sec % 60)
        return f"[{bar}] {pct}% | ETA {eta_min}m {eta_s}s"
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = {}
        for idx, cid in enumerate(client_ids, 1):
            print(f"[queue {idx}/{total}] {cid}", flush=True)
            futures[ex.submit(_run_one, cid, retries)] = cid
            if stagger and idx < total:
                time.sleep(stagger)
        done = 0
        durations = []
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            done += 1
            durations.append(res.get("duration", 0))
            idx_str = f"[{done}/{total}]"
            dur_str = f"{res['duration']:.1f}s"
            bar_str = progress_line(done, durations)
            print(f"{idx_str} {res['client']} → {res['status']} in {dur_str} | {bar_str}", flush=True)
    total_dur = time.time() - start
    print(f"Completed {total} clients in {total_dur/60:.1f} minutes", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-workers", type=int, default=2, help="Parallel workers (reduce to avoid rate limits)")
    parser.add_argument("--stagger", type=float, default=3.0, help="Seconds to wait between queueing jobs")
    parser.add_argument("--retries", type=int, default=2, help="Retries on rate limit or transient errors")
    args = parser.parse_args()
    if not CLIENT_IDS:
        print("No client ids provided.")
        return
    run_for_clients(CLIENT_IDS, max_workers=args.max_workers, stagger=args.stagger, retries=args.retries)


if __name__ == "__main__":
    main()


