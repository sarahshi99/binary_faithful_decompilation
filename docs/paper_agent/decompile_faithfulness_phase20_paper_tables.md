# Decompilation Faithfulness Phase 20 Paper Tables

## Main Results

| Dataset | Candidates | Paired cases | Fixture AUC | Static AUC | Final AUC | Detection | Avg inputs | Missed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Public static-hard | 478 | 50 | 0.9211 | 0.6806 | 1.0000 | 1.0000 | 6.64 | 0 |
| LLM-public | 136 | 24 | 0.9741 | 0.7759 | 1.0000 | 1.0000 | 6.69 | 0 |
| Ghidra | 166 | 26 | 0.5000 | 0.8207 | 1.0000 | 1.0000 | 6.97 | 0 |

## Stability And Runtime

| Dataset | AUC | AUC CI95 | Detection | Detection CI95 | Total seconds | P95 sec/cand | Input evals/sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| Public static-hard | 1.0000 | [1.0000, 1.0000] | 1.0000 | [1.0000, 1.0000] | 85.60 | 0.0923 | 37.05 |
| LLM-public | 1.0000 | [1.0000, 1.0000] | 1.0000 | [1.0000, 1.0000] | 7.94 | 0.0874 | 114.65 |
| Ghidra | 1.0000 | [1.0000, 1.0000] | 1.0000 | [1.0000, 1.0000] | 11.21 | 0.1031 | 103.25 |

## Ablation

Each cell is `AUC / detection / missed`.

| Method | Public static-hard | LLM-public | Ghidra |
|---|---:|---:|---:|
| Fixture-neighbor | 1.0000 / 1.0000 / 0 | 1.0000 / 1.0000 / 0 | 0.9891 / 0.9730 / 2 |
| Operator-char-first | 0.9889 / 0.9612 / 10 | 0.9914 / 0.9722 / 1 | 0.9565 / 0.9459 / 4 |
| Source-literal interleave | 1.0000 / 1.0000 / 0 | 1.0000 / 1.0000 / 0 | 1.0000 / 1.0000 / 0 |

## Ghidra Risk Families

| Risk family | Paired cases | AUC | Detection | Missed |
|---|---:|---:|---:|---:|
| loop | 9 | 1.0000 | 1.0000 | 0 |
| boundary | 7 | 1.0000 | 1.0000 | 0 |
| branch | 6 | 1.0000 | 1.0000 | 0 |
| nonnegative_domain | 5 | 1.0000 | 1.0000 | 0 |
| positive_domain | 5 | 1.0000 | 1.0000 | 0 |
| digits | 4 | 1.0000 | 1.0000 | 0 |
| division | 4 | 1.0000 | 1.0000 | 0 |
| multi_arg | 4 | 1.0000 | 1.0000 | 0 |
| recursion | 4 | 1.0000 | 1.0000 | 0 |
| sign_zero | 4 | 1.0000 | 1.0000 | 0 |
| char_boundary | 3 | 1.0000 | 1.0000 | 0 |
| comparison | 3 | 1.0000 | 1.0000 | 0 |
| conversion | 3 | 1.0000 | 1.0000 | 0 |

## LaTeX Drafts

### Main Result LaTeX

```latex
\begin{tabular}{lrrrrrrrr}
\toprule
Dataset & Cand. & Cases & Fixture & Static & Final & Detect. & Avg. Inp. & Miss \\
\midrule
Public static-hard & 478 & 50 & 0.9211 & 0.6806 & 1.0000 & 1.0000 & 6.64 & 0 \\
LLM-public & 136 & 24 & 0.9741 & 0.7759 & 1.0000 & 1.0000 & 6.69 & 0 \\
Ghidra & 166 & 26 & 0.5000 & 0.8207 & 1.0000 & 1.0000 & 6.97 & 0 \\
\bottomrule
\end{tabular}
```

### Ablation LaTeX

```latex
\begin{tabular}{lrrr}
\toprule
Method & Public & LLM-public & Ghidra \\
\midrule
Fixture-neighbor & 1.0000/1.0000/0 & 1.0000/1.0000/0 & 0.9891/0.9730/2 \\
Operator-char-first & 0.9889/0.9612/10 & 0.9914/0.9722/1 & 0.9565/0.9459/4 \\
Source-literal interleave & 1.0000/1.0000/0 & 1.0000/1.0000/0 & 1.0000/1.0000/0 \\
\bottomrule
\end{tabular}
```

### Runtime LaTeX

```latex
\begin{tabular}{lrrr}
\toprule
Dataset & Total s & P95 s/cand. & Input evals/s \\
\midrule
Public static-hard & 85.60 & 0.0923 & 37.05 \\
LLM-public & 7.94 & 0.0874 & 114.65 \\
Ghidra & 11.21 & 0.1031 & 103.25 \\
\bottomrule
\end{tabular}
```
