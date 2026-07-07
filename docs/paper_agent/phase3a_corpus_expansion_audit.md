# Phase 3a Corpus Expansion Audit

Created: 2026-07-07T11:11:22Z

Scope: pre-candidate corpus audit only. No candidate generation, semantic labeling, auditor policy, libFuzzer run, budget curve, or auditor result table was run.

## Decision

- Status: `no_expansion_feasible_above_80`
- Maximum feasible target across 80..120: `80`
- Maximum feasible target among requested targets: `80`
- Expansion target: `None`
- Reason: `project_capacity_and_dominance_constraints`
- V1 selected functions: `80`
- V1 function/fixture seal: `2bba63e1a191050f2ec0e15a8f58ed7eff9a5c9bf1f21b672b7ab9bfc64c1494`

No v2 selected-functions file or v2 seal is created because no target above 80 is feasible without violating project-capacity and dominance constraints.

## Why Selection Stopped At 80

- Eligible functions: `111`
- Selected functions: `80`
- Unselected eligible functions: `31`
- Strict 10-per-project capacity: `78`
- Largest project: `ccan` with `43` eligible functions
- Eligible functions outside largest project: `68`

The stop is due to project-capacity and dominance constraints. It is not due to argument-count quota, structural quota, sampler nondeterminism, a conservative amendment, candidate results, semantic labels, witnesses, or auditor behavior.

## Population Summaries

- Eligible by project: `{"brotli": 3, "c-ares": 1, "ccan": 43, "cmark": 9, "freetype": 2, "htslib": 8, "jansson": 1, "json-c": 1, "klib": 3, "libevent": 4, "libidn2": 2, "libucl": 2, "libuv": 3, "libxdiff": 1, "lz4": 1, "mpack": 1, "nanoprintf": 10, "nghttp2": 4, "open62541": 2, "pcre2": 1, "zstd": 9}`
- Eligible by argument count: `{"1": 91, "2": 12, "3": 8}`
- Eligible by domain size: `{"11": 3, "128": 87, "4096": 20, "5": 1}`
- Eligible structural features: `{"bitwise": 40, "branches4": 4, "interacting_args": 17, "lookup": 8, "loop": 12, "switch_like": 1}`
- Selected by project: `{"brotli": 3, "c-ares": 1, "ccan": 12, "cmark": 9, "freetype": 2, "htslib": 8, "jansson": 1, "json-c": 1, "klib": 3, "libevent": 4, "libidn2": 2, "libucl": 2, "libuv": 3, "libxdiff": 1, "lz4": 1, "mpack": 1, "nanoprintf": 10, "nghttp2": 4, "open62541": 2, "pcre2": 1, "zstd": 9}`
- Selected by argument count: `{"1": 60, "2": 12, "3": 8}`
- Selected structural features: `{"bitwise": 27, "branches4": 3, "interacting_args": 17, "lookup": 8, "loop": 8, "switch_like": 1}`
- Unselected by project: `{"ccan": 31}`

## Target Feasibility

| Target | Strict cap capacity | Dominance cap | Dominance capacity | Feasible | Main reasons |
| --- | ---: | ---: | ---: | --- | --- |
| 120 | 78 | 10 | 78 | False | insufficient_total_eligible_functions, strict_project_cap_capacity_shortfall, dominance_share_capacity_shortfall, largest_project_would_exceed_share_goal |
| 111 | 78 | 11 | 79 | False | strict_project_cap_capacity_shortfall, dominance_share_capacity_shortfall, largest_project_would_exceed_share_goal |
| 104 | 78 | 10 | 78 | False | strict_project_cap_capacity_shortfall, dominance_share_capacity_shortfall, largest_project_would_exceed_share_goal |
| 100 | 78 | 10 | 78 | False | strict_project_cap_capacity_shortfall, dominance_share_capacity_shortfall, largest_project_would_exceed_share_goal |
| 96 | 78 | 14 | 82 | False | strict_project_cap_capacity_shortfall, dominance_share_capacity_shortfall, largest_project_would_exceed_share_goal |
| 90 | 78 | 13 | 81 | False | strict_project_cap_capacity_shortfall, dominance_share_capacity_shortfall, largest_project_would_exceed_share_goal |
| 80 | 78 | 12 | 80 | True | strict_project_cap_capacity_shortfall |

## Guards

- Candidate/label artifacts absent: `True`
- Pre-existing v2 artifacts absent: `True`
- Candidate generation: `not_run`
- Semantic labeling: `not_run`
- Auditor execution: `not_run`
