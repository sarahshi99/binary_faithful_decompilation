# Decompilation Faithfulness Phase 2 CPU Smoke

- Smoke gate passed: `True`
- Cases: `8`
- Candidates: `17`
- Compile pass count: `17`
- Behavior labels: `{'faithful': 9, 'plausible_wrong': 8, 'compile_fail': 0}`
- Fixture collapse: `False`
- Non-oracle probe count: `1`
- Trace pairwise AUC: `0.9444`

This smoke validates the manifest, compile/behavior gate, metadata sidecar, and Dynamic Trace v2 path without using GPU.
