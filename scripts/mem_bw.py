#!/usr/bin/env python3
# numpy STREAM-triad style memory bandwidth probe (multi-thread via multiprocessing)
import numpy as np, time, multiprocessing as mp, os
N = 400_000_000  # 400M float64 = 3.2GB per array, 9.6GB working set
def worker(k, n):
    a = np.ones(n // n, dtype=np.float64)  # tiny init
    a = np.full(n, 1.0); b = np.full(n, 2.0); c = np.empty(n)
    t0 = time.perf_counter()
    np.multiply(a, b, out=c)  # triad-ish: reads 2 arrays writes 1
    dt = time.perf_counter() - t0
    return len(a) * 3 * 8 / dt
if __name__ == "__main__":
    n = N
    for t in (1, 8, min(16, mp.cpu_count())):
        procs = [mp.Process(target=lambda: None)]
        # use threads-of-processes: simplest fork pool
        with mp.Pool(t) as p:
            res = p.starmap(worker, [(0, n // t)] * t)
        gb = sum(res) / 1e9
        print(f"threads={t:2d}  triad BW = {gb:7.1f} GB/s")
    print("cpu_count", mp.cpu_count())
