# -*- coding: utf-8 -*-
"""Round 2: warm measurement of ComfyUI perf flags on card B. Per variant:
boot comfy (stdout->log), warm bench (discarded), timed bench, kill."""
import json, subprocess, time, os, re

PY = r"C:\ComfyUI\venv\Scripts\python.exe"
CUI = r"C:\ComfyUI\ComfyUI"
BENCH = r"E:\ComfyUI-models\workflows\contest\h3_bench_cw.py"
OUT = r"E:\ComfyUI-models\workflows\contest\flag_bench_results2.jsonl"
SLOG = r"C:\Users\willi\AppData\Local\hermes\cache\scratch\comfy_start"

VARIANTS = [
    ("base",     []),
    ("ckattn",   ["--use-ck-attention"]),
    ("fp8mm",    ["--fast", "fp8_matrix_mult"]),
    ("autotune", ["--fast", "autotune"]),
    ("fp16acc",  ["--fast", "fp16_accumulation"]),
    ("triton",   ["--enable-triton-backend"]),
]
BENCH_ARGS = ["--label", "flagbench2", "--port", "8188", "--steps", "4", "--ctx", "0",
              "--w", "512", "--h", "288", "--length", "121",
              "--dit", "minimax_h3_ref2va-Q4_K_M.gguf", "--timeout", "600"]

def wait_up(p, limit=150):
    t0 = time.time()
    while time.time()-t0 < limit:
        if p.poll() is not None: return False
        try:
            import urllib.request; urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=5).read()
            return True
        except Exception: time.sleep(3)
    return False

env = dict(os.environ, HIP_VISIBLE_DEVICES="0")
for name, extra in VARIANTS:
    logf = open(f"{SLOG}_{name}.log", "w", encoding="utf-8", errors="replace")
    p = subprocess.Popen([PY, "main.py", "--port", "8188", "--disable-smart-memory"] + extra,
                         cwd=CUI, env=env, stdout=logf, stderr=subprocess.STDOUT)
    rec = {"variant": name, "flags": extra}
    ok = wait_up(p)
    rec["started"] = ok
    times = []
    if ok:
        for i in range(2):  # run 1 = warmup discarded, run 2 = timed
            t0 = time.time()
            r = subprocess.run([PY, BENCH]+BENCH_ARGS, capture_output=True, text=True, timeout=700)
            el = time.time()-t0
            line = (r.stdout or "").strip().splitlines()
            if i == 1:
                rec["wall2"] = round(el, 1)
                rec["bench2"] = line[-1] if line else ""
            times.append(round(el,1))
    rec["runs"] = times
    subprocess.run(["cmd", "/c", "taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    logf.close(); time.sleep(6)
    # what did comfy claim about backends/flags?
    txt = open(f"{SLOG}_{name}.log", encoding="utf-8", errors="replace").read()
    keys = [l.strip() for l in txt.splitlines()
            if re.search(r"attention|optimization|fast|triton|kitchen|fp8|fp16|backend|autotune|enabled", l, re.I)]
    rec["startup_notes"] = keys[:8]
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False)+"\n")
    print("DONE", name, times, flush=True)

p = subprocess.Popen([PY, "main.py", "--port", "8188", "--disable-smart-memory"],
                     cwd=CUI, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("PROD_COMFY_PID", p.pid, flush=True)
