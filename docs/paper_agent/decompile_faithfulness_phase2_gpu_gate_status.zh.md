# Decompilation Faithfulness Phase 2 GPU Gate Status

## 当前结论

CPU-only Phase 2 smoke 已通过，但 GPU smoke 没有启动。

原因：用户要求只有在 GPU 2/3 没有其他任务时才开启 GPU；当前 GPU 2 和 GPU 3 都有活跃 compute 进程。

## CPU Smoke 结果

- Smoke gate passed: `True`
- Candidates: `17`
- Compile pass count: `17`
- Behavior labels: `faithful=9`, `plausible_wrong=8`, `compile_fail=0`
- Fixture collapse: `False`
- Non-oracle probe count: `1`
- Trace pairwise AUC: `0.9444`
- Manifest: `analysis_outputs/decompile_faithfulness/phase2_cpu_smoke/manifest.json`
- Records: `analysis_outputs/decompile_faithfulness/phase2_cpu_smoke/records.jsonl`

解释：CPU smoke 已经验证 manifest、metadata sidecar、compile/behavior gate、Dynamic Trace v2 链路可以跑通，而且包含一个 fixture-overfit probe，证明不是只在跑 fixture oracle。

## GPU 2/3 状态

`nvidia-smi` 快照显示：

| GPU | Memory used | Utilization | Active processes |
|---|---:|---:|---|
| 2 | `39071 MiB` | `99%` | Carla `6465 MiB`; python `32546 MiB` |
| 3 | `39177 MiB` | `44%` | Carla `6562 MiB`; python `32554 MiB` |

因此本轮没有执行任何 GPU generation，也没有设置 `CUDA_VISIBLE_DEVICES=2,3` 启动模型。

## 本地模型探针

- `torch`: `true`
- `transformers`: `true`
- `accelerate`: `true`
- Dream-Coder cache dir exists: `true`
- Dream-Coder shallow `config.json` found: `false`

解释：Python 生成工具栈存在，但本轮没有加载模型。即使模型可加载，GPU 2/3 当前也不满足空闲条件。

## 下一步

等 GPU 2/3 空闲后，先重新运行 GPU gate：

```bash
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv,noheader
```

只有当 GPU 2/3 没有活跃 compute 进程，再继续做 local model loadability probe 和 GPU smoke。不要在当前状态下启动 GPU。
