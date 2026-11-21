# -*- coding: utf-8 -*-
"""Benchmark ComfyUI perf flags on card B (R9700) with a short H3 bench.
Variants: baseline / ck-attention / fp8_matrix_mult / autotune / fp16_accumulation / triton-backend
Each: fresh ComfyUI on :8188, small 512x288x33f 4-step job, record exec wall time."""
import json, subprocess, time, sys, os, urllib.request

PY = r"C:\ComfyUI\venv\Scripts\python.exe"
CUI = r"C:\ComfyUI\ComfyUI"
BENCH = r"E:\ComfyUI-models\workflows\contest\h3_bench_cw.py"
OUT = r"E:\ComfyUI-models\workflows\contest\flag_bench_results.jsonl"

VARIANTS = [
    ("base",     []),
    ("ckattn",   ["--use-ck-attention"]),
    ("fp8mm",    ["--fast", "fp8_matrix_mult"]),
    ("autotune", ["--fast", "autotune"]),
    ("fp16acc",  ["--fast", "fp16_accumulation"]),
    ("triton",   ["--enable-triton-backend"]),
]
BENCH_ARGS = ["--label", "flagbench", "--port", "8188", "--steps", "4", "--ctx", "0",
              "--w", "512", "--h", "288", "--length", "33",
              "--dit", "minimax_h3_ref2va-Q4_K_M.gguf", "--timeout", "600"]

def get(path, timeout=5):
    return json.loads(urllib.request.urlopen("http://127.0.0.1:8188"+path, timeout=timeout).read())

def wait_up(p, limit=150):
    t0 = time.time()
    while time.time()-t0 < limit:
        if p.poll() is not None:
            return False
        try:
            get("/system_stats"); return True
        except Exception:
            time.sleep(3)
    return False

env = dict(os.environ, HIP_VISIBLE_DEVICES="0")
results = []
for name, extra in VARIANTS:
    rec = {"variant": name, "flags": extra}
    args = [PY, "main.py", "--port", "8188", "--disable-smart-memory"] + extra
    p = subprocess.Popen(args, cwd=CUI, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rec["comfy_pid"] = p.pid
    ok = wait_up(p)
    rec["started"] = ok
    if ok:
        r = subprocess.run([PY, BENCH]+BENCH_ARGS, capture_output=True, text=True, timeout=700)
        line = (r.stdout or "").strip().splitlines()
        rec["bench_out"] = line[-2:] if line else []
        rec["bench_err"] = (r.stderr or "").strip()[-300:] if r.returncode else ""
    else:
        rec["bench_err"] = "comfy failed to start with flags"
    subprocess.run(["cmd", "/c", "taskkill", "/F", "/T", "/PID", str(p.pid)],
                   capture_output=True)
    time.sleep(8)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False)+"\n")
    print("DONE", name, rec.get("bench_out"), flush=True)

# leave the production instance running again
p = subprocess.Popen([PY, "main.py", "--port", "8188", "--disable-smart-memory"],
                     cwd=CUI, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("PROD_COMFY_PID", p.pid, flush=True)
