# 雙 R9700 (RDNA4 / gfx1201) 實測記錄 — Dual R9700 Field Notes

Willie 嘅「世界之樹」雙 R9700 機：一張做 LLM 主線推理（Strata Qwen3.8-Flash-Next 125B MoE, GGUF IQ3），一張做生成線（ComfyUI / MiniMax H3）。呢個倉係我哋嘅**原始實測數據＋調校記錄**，全部公開，希望同一班行呢條路嘅朋友互相參考、一同成長。

Dual-R9700 production box: Card A = LLM inference (Strata, Qwen3.8-Flash-Next 125B MoE IQ3-GGUF), Card B = generation (ComfyUI / MiniMax-H3). Raw benchmark data + tuning notes, fully open — sharing to help everyone moving along this path grow together.

## 硬件 / Hardware
- 2x AMD Radeon R9700 (gfx1201, 32GB) — MSI MPG X870E, 96GB DDR5-6000 (EXPO 未開, 現行 3600 MT/s — 呢個係已識別未修復嘅主要瓶頸)
- Windows 11 + Adrenalin 26.11.2；LLM 主線跑 Windows，benchmark/fork 對照跑 WSL2 (Ubuntu-24.04, ROCm 7.2 via /dev/dxg)

## 核心實測結論 / Key measured findings (2026-11)
1. **27B Q4_K_XL decode 係 DRAM roofline**：單卡 ~31 t/s @3600MT/s 系統內存；numpy triad 實測內存頻寬 ~32.7 GB/s。GPU 核心超頻對 decode 幾乎無效
2. **MTP 投機解碼係最大單著**：llama.cpp `--mtp` 54-56 t/s（接受率 59-70%）— 即 +75%
3. **Prefill**：flash-attn on + ub 1024 = +13-14%（659→744-753 t/s）
4. **Fork 對照實驗**（rdna-boosts、The-Rock8 vs 同 commit plain upstream llama.cpp，相同 grid）：**吞吐無明顯差異**——呢啲 fork 提供功能集而唔係速度；現行 Qwen3.8 GGUF 用 upstream 最穩
5. Strata 125B @卡A：decode ~88-94 t/s（MTP＋KV int8＋prefix cache）。`GPU_MAX_HW_QUEUES=1 vs 2` 待測

## 已知坑 / Pitfalls we hit
- **pick_ordinal**：Strata pin 卡要用 PCI bus ordinal（bus03=卡A），hipMemGetInfo 報告唔準，睇卡用 ADL
- **ROCm 10.2 known issue**：ComfyUI 用 AOTriton attention backend 喺部分 Radeon 倒退 — 用 CK attention
- **Windows SAC**：腳本啟動嘅下載 exe 會被靜擋
- **WSL build**：The-Rock8 內嵌 llama-ui-embed CMake 失敗 → `-DLLAMA_BUILD_UI=OFF`
- 雙卡共存 ComfyUI 常開：生成卡啟動要 `HIP_VISIBLE_DEVICES=0`

## 目錄 / Layout
- `reports/` — 兩份完整報告（第一夜 L1 網格＋L2/L3 fork 對照＋DfAM-style Monday runbook；週末生態scan）
- `data/` — 原始 llama-bench JSONL（baseline / plain×2 / rdna-boosts×2 / Rock8×3，同 commit 對照）＋ bench_notes
- `scripts/` — 評測網格、內存頻寬 triad、H3 time-slice bench、WSL build chain
- 完整 repro：每份報告入面有原始 command；模型唔隨倉分發（license）

## 邀請 / 一同發展
呢個生態（gfx1201）啱啱起步，好感恩已經有 NikoCloud / halonc / fcme 嘅單卡經驗鋪路；我哋都願意將自己每一步實測擺出嚟，雙卡 TP2（Radiance）準備落機，過程都會繼續公開。**歡迎得同我哋一樣嘅卡、或者唔同路徑嘅朋友，交流你嘅數據同心得**——重現唔同結果都係寶貴資訊，我哋會虛心跟每一條討論覆實，一齊將呢條路行寬。

*Data CC-BY 4.0 · code MIT · model weights not redistributed.*
