#!/bin/bash
set -x
export PATH="$HOME/.local/bin:$PATH"
M=/mnt/e/LLM/unsloth/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf
S=/mnt/c/Users/willi/AppData/Local/hermes/cache/scratch
export HIP_VISIBLE_DEVICES=0   # WSL idx0 = PCI 07:00.0 = 卡B（已驗證）
cd ~/bench/llama.cpp

# 1) rdna-boosts bench（同 Windows 基線同一 grid）
./build/bin/llama-bench -m "$M" -ngl 99 -fa 0 -ctk f16 -ctv f16 -ub 512,1024 -pg "512,128" -r 3 -o jsonl > "$S/bench_rdnaA.jsonl" 2>"$S/bench_rdnaA.err"
./build/bin/llama-bench -m "$M" -ngl 99 -fa 1 -ctk f16,q8_0 -ctv f16,q8_0 -ub 512,1024,2048 -pg "512,128" -r 3 -o jsonl > "$S/bench_rdnaB.jsonl" 2>"$S/bench_rdnaB.err"
echo RDNA_BENCH_DONE

# 2) plain 基線 build（同 fork point，冇 patch）
cd ~/bench
git -C llama.cpp worktree add --quiet -f ../llama-plain 4f9dfa0e3 2>/dev/null || true
cd ~/bench/llama-plain
cmake -B build -G Ninja -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1201 -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF > cmake_cfg.log 2>&1
cmake --build build -j 14 --target llama-bench > plain_build.log 2>&1 && echo PLAIN_BUILD_OK || tail -15 plain_build.log

# 3) plain 基線 bench
./build/bin/llama-bench -m "$M" -ngl 99 -fa 0 -ctk f16 -ctv f16 -ub 512,1024 -pg "512,128" -r 3 -o jsonl > "$S/bench_plainA.jsonl" 2>"$S/bench_plainA.err"
./build/bin/llama-bench -m "$M" -ngl 99 -fa 1 -ctk f16,q8_0 -ctv f16,q8_0 -ub 512,1024,2048 -pg "512,128" -r 3 -o jsonl > "$S/bench_plainB.jsonl" 2>"$S/bench_plainB.err"
echo PLAIN_BENCH_DONE
