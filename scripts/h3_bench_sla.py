#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""卡B 單卡速度實驗：比較不同 (steps, context window, DiT) 組合喺 289 幀 12 秒片嘅 wall time。
用法: python h3_bench_cw.py --label cw124 --steps 6 --ctx 124 --overlap 39 --port 8188
      --ctx 0 = 唔用 context window（對照）
"""
import json, urllib.request, urllib.error, uuid, time, argparse, os

API = "http://127.0.0.1:{port}"
BASE = r"E:\ComfyUI-models\workflows\H3_④NVFP4無審查TE+DiT_GGUF_已驗證25s_it.json"

def post(path, payload=None):
    req = urllib.request.Request(API.format(port=args.port) + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type":"application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=90).read())
    except urllib.error.HTTPError as e:
        return {"HTTP": e.code, "BODY": e.read().decode()[:2500]}

def get(path):
    return json.loads(urllib.request.urlopen(API.format(port=args.port) + path, timeout=60).read())

def build():
    wf = json.loads(json.dumps(json.load(open(BASE, encoding="utf-8"))))
    prompt = ("cinematic sword fight between a red-robed swordsman and a purple-robed warrior, "
              "dynamic camera orbit, dramatic lighting, no text")
    del wf["9"]
    wf["9"] = {"class_type":"MiniMaxH3ImageToVideo","inputs":{
        "clip":["2",0],"vae":["4",0],"prompt":prompt,
        "width":args.w,"height":args.h,"length":args.length}}
    wf["1"]["inputs"]["unet_name"] = args.dit
    wf["10"]["inputs"]["positive"] = ["9",0]
    wf["10"]["inputs"]["latent_image"] = ["9",1]
    wf["10"]["inputs"]["steps"] = args.steps
    wf["10"]["inputs"]["seed"] = args.seed
    wf["14"]["inputs"]["filename_prefix"] = "H3/" + args.label
    if args.ctx > 0:
        # MiniMaxH3ContextWindows: model 出嚟做分窗 attention（接 SigmaShift 節點 6 之後）
        wf["20"] = {"class_type":"MiniMaxH3ContextWindows","inputs":{
            "model":["6",0], "context_length":args.ctx, "context_overlap":args.overlap,
            "fuse_method":"pyramid", "freenoise":True, "split_conds_to_windows":False}}
        wf["10"]["inputs"]["model"] = ["20",0]
    if args.sla > 0:
        src_node = "20" if args.ctx > 0 else "6"
        wf["21"] = {"class_type":"H3SLAAttentionROCM","inputs":{
            "model":[src_node,0], "sparsity_ratio":args.sla, "block_size":"64",
            "protect_audio":True, "enabled":True, "dense_backend":"comfy_kitchen"}}
        wf["10"]["inputs"]["model"] = ["21",0]
    return wf

args = argparse.ArgumentParser()
args.add_argument("--label", required=True)
args.add_argument("--port", type=int, default=8188)
args.add_argument("--steps", type=int, default=6)
args.add_argument("--ctx", type=int, default=0)
args.add_argument("--overlap", type=int, default=39)
args.add_argument("--w", type=int, default=1344)
args.add_argument("--h", type=int, default=768)
args.add_argument("--length", type=int, default=289)
args.add_argument("--seed", type=int, default=20261114)
args.add_argument("--dit", default="minimax_h3_fl2va-Q3_K_M.gguf")
args.add_argument("--timeout", type=int, default=5400)
args.add_argument("--sla", type=float, default=0.0)
args = args.parse_args()

wf = build()
r = post("/prompt", {"prompt": wf, "client_id": uuid.uuid4().hex})
if "prompt_id" not in r:
    print("SUBMIT_FAIL", json.dumps(r, ensure_ascii=False)[:2000], flush=True); raise SystemExit(2)
pid = r["prompt_id"]
print(f"[{args.label}] pid={pid} steps={args.steps} ctx={args.ctx} dit={args.dit}", flush=True)
t0 = time.time(); exec_start = None
while time.time()-t0 < args.timeout:
    time.sleep(10)
    if exec_start is None:
        q = get("/queue")
        if any(it[1]==pid for it in q.get("queue_running",[])): exec_start = time.time()
    h = get(f"/history/{pid}")
    if pid in h:
        st = h[pid]["status"]
        el = time.time()-t0; ex = (time.time()-exec_start) if exec_start else None
        outs = [f"{o.get('subfolder','')}/{f.get('filename')}" for o in h[pid].get("outputs",{}).values()
                for f in (o.get("images") or [])+(o.get("videos") or [])+(o.get("gifs") or [])]
        print(f"[{args.label}] status={st.get('status_str')} total={el:.0f}s exec={ex and round(ex)}s "
              f"s/it={ex and round(ex/args.steps,1)} out={outs}", flush=True)
        if st.get("status_str")!="success":
            for m in (st.get("messages") or [])[:3]: print("  msg:", json.dumps(m,ensure_ascii=False)[:400], flush=True)
        json.dump({"label":args.label,"steps":args.steps,"ctx":args.ctx,"overlap":args.overlap,
                   "w":args.w,"h":args.h,"length":args.length,"dit":args.dit,
                   "total_s":el,"exec_s":ex,"s_per_it":(ex/args.steps) if ex else None,
                   "status":st.get("status_str"),"files":outs},
                  open(rf"E:\ComfyUI-models\workflows\contest\_bench_{args.label}.json","w",encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        break
else:
    print(f"[{args.label}] TIMEOUT", flush=True)
