# R9700/gfx1201 前人經驗（2026-11-21 夜搜，供 L1/L2 用）

## 直接相關嘅 repo／筆記
1. **NikoCloud/r9700-local-inference-notes** — 同我哋完全同卡（R9700 32GB＋9070XT 雙卡）：
   - llama.cpp + MTP n_max=2 → 61.7 t/s；n-gram→MTP 鏈 code 場景 1.6–2.9×
   - vLLM MXFP4 W4A8（RDNA4 fp8 WMMA）單卡 prefill 2.6–3.5×
   - 雙卡：PP=2 不均層拆 → KV cache 3.6×；TP=2 要 RCCL；**混合卡死喺 Tensile GEMM**
   - ComfyUI `--cache-ram` 上限，唔然食盡系統 RAM（98-229s → 25-28s/圖）
   - LEVERS.md＝逐 knob 量度差值；MISTAKES.md＝所有坑；47 條 benchmark 規則
2. **The-Monk/The-Rock8** — RDNA4 native int4/fp8 llama.cpp：int4 GEMV decode 已達 DRAM roofline 95-97%（631 GB/s）→ **decode 無太多水可擠，升級位喺 prefill＋投機**；hipBLASLt per-format prefill routes（env 門控）＋ self-tuning algo cache（gfx1201 冇 cost model）→ +15.6% pp1024
3. **stew675/llama-cpp-rdna-boosts** — RDNA/HIP patches default-on；hipBLASLt 開住 → decode 最多 +15%（ROCBLAS_USE_HIPBLASLT）
4. **achyudh/llama.cpp fork** — RDNA4 kernel 優化＋Adaptive KV Streaming：16GB 卡行 27B 262K ctx，80+ t/s decode／1400 t/s prefill；launch 環境變數 GPU_MAX_HW_QUEUES=2、force async/graph queue
5. **kr4ckhe4d/local-llm-benchmarks**（9070XT gfx1201 實測）：
   - **`-ub`（ubatch）最被忽視**：ctx 預算夠就加大，+70%
   - KV quant：**q8_0/q8_0 同 f16 一樣快、半個內存**；混 precision 冇著數（-23% pp）
   - **threads 用 16，唔好用 32**（SMT 撞車）
   - 留意其他程序食 VRAM（DaVinci 食 10.4GB 呢類）
6. **雙 R9700**（Puget 測試）：27B Q4_K_M 兩卡層拆 **23.4 t/s 單用戶（比單卡慢！跨卡 PCIe 開銷）**，但 4-8 用戶聚合 55.7 t/s；ComfyUI 兩卡唔會翻倍
7. back2gaming：R9700 27B 31.7 t/s（32GB 全 VRAM，32K ctx）；功耗 395W 全機

## 今晚 grid 候選（27B 喺卡B）
- baseline（而家 launcher 嘅 flag）
- -ub 加大（512/1024/2048）
- ctk/ctv q8_0/q8_0 vs 預設
- -t 16 vs 24
- fa on/off
- MTP spec decode（--spec-type draft-mtp）開/關
- GPU_MAX_HW_QUEUES=2
- hipBLASLt tuning（HIPBLASLT_TUNING_MODE／tune file，若 build 支援）

## 鐵律
- 卡A 主線唔好郁；实验全部 HIP_VISIBLE_DEVICES=0（卡B）
- benchmark 用 llama-bench pp512/tg128 標準組
- 07:00 前還原：起返 ComfyUI、殺測試 server
