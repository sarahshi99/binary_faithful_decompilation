# Decompilation Faithfulness Phase 7 CodeFuse-DeBench Import

- Verdict: `pass-phase7-codefuse-import`
- Benchmark: `CodeFuse-DeBench`
- Import mode: `partial_git_tree_src_scalar_integer_functions`
- Source files discovered: `8`
- Imported functions: `56`
- Oracle ready: `56`
- Compile pass: `56`
- Fixture pass: `56`

## Imported Functions

| Case | Signature | Oracle ready | Risks |
|---|---|---:|---|
| `codefuse_1_sequential_ops` | `int sequential_ops(int a, int b, int c)` | `True` | `public_benchmark, operator_boundary, multi_arg` |
| `codefuse_1_single_if` | `int single_if(int x)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_1_nested_if_2` | `int nested_if_2(int a, int b)` | `True` | `public_benchmark, branch, operator_boundary, multi_arg` |
| `codefuse_1_nested_if_deep` | `int nested_if_deep(int a, int b, int c, int d, int e)` | `True` | `public_benchmark, branch, operator_boundary, multi_arg` |
| `codefuse_1_if_elseif_chain` | `int if_elseif_chain(int x)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_1_if_elseif_long` | `int if_elseif_long(int x)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_1_switch_small` | `int switch_small(int op)` | `True` | `public_benchmark, operator_boundary` |
| `codefuse_1_switch_large` | `int switch_large(int op)` | `True` | `public_benchmark, operator_boundary` |
| `codefuse_1_switch_default` | `int switch_default(int op)` | `True` | `public_benchmark, operator_boundary` |
| `codefuse_1_switch_fallthrough` | `int switch_fallthrough(int op)` | `True` | `public_benchmark, operator_boundary` |
| `codefuse_1_loop_for_fixed` | `int loop_for_fixed(int n)` | `True` | `public_benchmark, loop, operator_boundary` |
| `codefuse_1_loop_while` | `int loop_while(int x)` | `True` | `public_benchmark, loop, operator_boundary` |
| `codefuse_1_loop_dowhile` | `int loop_dowhile(int x)` | `True` | `public_benchmark, loop, operator_boundary` |
| `codefuse_1_loop_nested` | `int loop_nested(int m, int n)` | `True` | `public_benchmark, loop, operator_boundary, multi_arg` |
| `codefuse_1_loop_break` | `int loop_break(int target)` | `True` | `public_benchmark, branch, loop, operator_boundary` |
| `codefuse_1_loop_continue` | `int loop_continue(int n)` | `True` | `public_benchmark, branch, loop, operator_boundary` |
| `codefuse_1_goto_forward` | `int goto_forward(int x)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_1_goto_backward` | `int goto_backward(int x)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_1_ternary_op` | `int ternary_op(int a, int b)` | `True` | `public_benchmark, operator_boundary, multi_arg` |
| `codefuse_1_loop_multi_exit` | `int loop_multi_exit(int target)` | `True` | `public_benchmark, branch, loop, operator_boundary` |
| `codefuse_1_multi_return` | `int multi_return(int x)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_1_conditional_return` | `int conditional_return(int x)` | `True` | `public_benchmark, operator_boundary` |
| `codefuse_1_loop_complex_cond` | `int loop_complex_cond(int x)` | `True` | `public_benchmark, loop, operator_boundary` |
| `codefuse_1_loop_modify_var` | `int loop_modify_var(int n)` | `True` | `public_benchmark, branch, loop, operator_boundary` |
| `codefuse_1_state_machine` | `int state_machine(int event, int state)` | `True` | `public_benchmark, branch, operator_boundary, multi_arg` |
| `codefuse_1_obfuscated_cf` | `int obfuscated_cf(int x)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_1_opaque_predicate` | `int opaque_predicate(int x)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_2_process_char` | `char process_char(char c)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_2_process_short` | `short process_short(short a, short b)` | `True` | `public_benchmark, operator_boundary, multi_arg` |
| `codefuse_2_process_int` | `int process_int(int x)` | `True` | `public_benchmark, operator_boundary` |
| `codefuse_2_process_bool` | `_Bool process_bool(int x)` | `True` | `public_benchmark, operator_boundary` |
| `codefuse_3_local_vars` | `int local_vars(int x)` | `True` | `public_benchmark` |
| `codefuse_3_local_array` | `int local_array(int n)` | `True` | `public_benchmark, loop, operator_boundary` |
| `codefuse_3_large_stack_frame` | `int large_stack_frame()` | `True` | `public_benchmark, loop, operator_boundary` |
| `codefuse_3_vla_stack` | `int vla_stack(int n)` | `True` | `public_benchmark, branch, loop, operator_boundary` |
| `codefuse_4_cdecl_func` | `int cdecl_func(int a, int b)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_stdcall_func` | `int stdcall_func(int a, int b)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_fastcall_func` | `int fastcall_func(int a, int b, int c)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_arm_aapcs_func` | `int arm_aapcs_func(int a, int b, int c, int d, int e)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_mips_func` | `int mips_func(int a, int b, int c, int d)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_amd64_sysv_func` | `int amd64_sysv_func(int a, int b, int c, int d, int e, int f)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_ms_x64_func` | `int ms_x64_func(int a, int b, int c, int d, int e)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_vectorcall_func` | `int vectorcall_func(int a, int b, int c, int d)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_func_no_args` | `int func_no_args(void)` | `True` | `public_benchmark` |
| `codefuse_4_func_many_args` | `int func_many_args(int a, int b, int c, int d, int e, int f, int g, int h)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_param_by_value_int` | `int param_by_value_int(int x)` | `True` | `public_benchmark, operator_boundary` |
| `codefuse_4_param_order_dep` | `int param_order_dep(int a, int b)` | `True` | `public_benchmark, multi_arg` |
| `codefuse_4_ret_basic_type` | `int ret_basic_type(int x)` | `True` | `public_benchmark` |
| `codefuse_4_func_a` | `int func_a(int x)` | `True` | `public_benchmark` |
| `codefuse_4_func_b` | `int func_b(int x)` | `True` | `public_benchmark` |
| `codefuse_4_ret_complex_expr` | `int ret_complex_expr(int x, int y, int z)` | `True` | `public_benchmark, operator_boundary, multi_arg` |
| `codefuse_4_ret_multi_branch` | `int ret_multi_branch(int op)` | `True` | `public_benchmark` |
| `codefuse_5_23_param_multi_branch_compile` | `int param_multi_branch_compile(int x)` | `True` | `public_benchmark, branch, operator_boundary` |
| `codefuse_5_23_my_func` | `int my_func(int x)` | `True` | `public_benchmark` |
| `codefuse_7_param_integer_overflow` | `int param_integer_overflow(int a, int b)` | `True` | `public_benchmark, branch, operator_boundary, multi_arg` |
| `codefuse_7_param_implementation_defined` | `int param_implementation_defined()` | `True` | `public_benchmark, operator_boundary` |

## Interpretation

This import uses CodeFuse-DeBench source files as a public source-known benchmark seed. It intentionally keeps only scalar integer C functions that fit the current bounded dynamic trace harness. Pointer, array, floating-point, C++ and helper-dependent functions are deferred to later adapters.
