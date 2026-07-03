# Holdout Generation Seal Handoff

## Git

- Branch: `phase1d-holdout-generation-and-seal`
- HEAD at generation: `98dc9c61b8246b49096c52e4ac3de642b66ac530`
- Amendment commit: `3a0a65ff6c38da9dbd9a9f620a6b434d7fb3e1fa`
- Method freeze commit: `06dda89912103b94fc065d6f073581a7811154b1`
- Phase 1b correction commit: `a784d1c8195ae88a8b3233f8eef5cfd2c27d7b14`
- Phase 1c census commit: `4b4e552b2ea93f057c679a0eba662075e09203be`
- Phase 1c census seal hash: `74b2168a7b9f4e924c521d37df16b48ee776b9562b9c2d1c674147be2e2127ba`
- Final holdout seal hash: `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`

## Seeds And Domains

- Sampling seed: `2026070301`
- Fixture seed: `2026070302`
- Mutation seed: `2026070303`
- Exact domains: `{"bool": "{0, 1}", "char_signed_model": "[0, 127]", "signed_short_int_long_like": "[-32, 31]", "two_argument_rule": "complete Cartesian product", "unsigned_char": "[0, 127]", "unsigned_short_int_long_like": "[0, 63]"}`

## Selected Functions

- Selected-function count: `42`
- Selected-function counts by project: `{"BearSSL": 2, "TinyCC": 8, "chibicc": 1, "libb64": 2, "libtomcrypt": 2, "mbedtls": 2, "musl": 8, "sbase": 8, "sqlite": 8, "xxHash": 1}`

## Candidate And Label Counts

- Natural candidate attempts: `84`
- Natural compile-ready yield: `16`
- Natural semantic-wrong count: `0`
- Controlled candidate attempts: `84`
- Controlled compile-ready yield: `78`
- Controlled semantic-wrong count: `60`
- Natural exact-domain no-mismatch count: `16`
- Controlled exact-domain no-mismatch count: `18`
- Exact-label count: `168`
- Non-evaluable counts and reasons: `{"compile_failure": 73, "runtime_failure_1": 1}`
- Exclusion count: `7371`
- Sampling capacity under project cap: `42`
- Exhaustive execution count: `51328`

## Source-Literal Prevalence

```json
{
  "descriptive_only": true,
  "functions_with_char_literals": 23,
  "per_function": {
    "BearSSL::tools_names.c::hexval::0008::993a0d3d1ea6": 9,
    "BearSSL::tools_names.c::is_ign::0004::a92f16112529": 6,
    "TinyCC::arm64-asm.c::is_valid_movw_shift::0010::b17f74db7409": 0,
    "TinyCC::arm64-gen.c::arm64_pe_param_off::0009::790dfaa50add": 0,
    "TinyCC::conftest.c::isid::0001::8f9cf31cf5da": 7,
    "TinyCC::conftest.c::isspc::0002::8253a2dcd0bb": 1,
    "TinyCC::riscv64-gen.c::is_freg::0004::4c61127d0c8b": 0,
    "TinyCC::tccdbg.c::dwarf_uleb128_size::0003::d476151071dd": 0,
    "TinyCC::tcctools.c::le2belong::0001::9d35b2a4c6a7": 0,
    "TinyCC::x86_64-gen.c::using_regs::0004::b9ec9c9e28b6": 0,
    "chibicc::tokenize.c::from_hex::0005::45632cc30325": 7,
    "libb64::src_cdecode.c::base64_decode_value::0001::7b72285f2481": 2,
    "libb64::src_cencode.c::base64_encode_value::0001::6dca5895e15c": 1,
    "libtomcrypt::src_pk_asn1_der_generalizedtime_der_decode_generalizedtime.c::s_char_to_int::0001::7560b8026c5c": 10,
    "libtomcrypt::src_pk_asn1_der_utctime_der_decode_utctime.c::s_char_to_int::0001::f87ee5162c3b": 10,
    "mbedtls::library_x509.c::nibble_to_hex_digit::0015::b855ad07642b": 2,
    "mbedtls::library_x509_create.c::hex_to_int::0001::7aeb57347f91": 9,
    "musl::src_ctype_isalpha.c::isalpha::0001::279b5a02fc43": 1,
    "musl::src_ctype_iscntrl.c::iscntrl::0001::ca58b22988c2": 0,
    "musl::src_ctype_isgraph.c::isgraph::0001::42b3df97c421": 0,
    "musl::src_ctype_isspace.c::isspace::0001::93f674d2bcdd": 2,
    "musl::src_network_inet_pton.c::hexval::0001::a0a6dbc2a411": 4,
    "musl::src_regex_regcomp.c::hexval::0004::5a81c0c932f7": 4,
    "musl::src_stdlib_abs.c::abs::0001::7d806d7b2171": 0,
    "musl::src_stdlib_llabs.c::llabs::0001::b58997ecb0f1": 0,
    "sbase::cron.c::isleap::0001::0fde71268ef6": 0,
    "sbase::dc.c::isqrt::0015::836b73bf0246": 0,
    "sbase::find.c::cmp_eq::0002::16afa3d71aab": 0,
    "sbase::find.c::cmp_gt::0001::7383663fc3bf": 0,
    "sbase::find.c::cmp_lt::0003::3ff7fb5ec166": 0,
    "sbase::libutil_crypt.c::hexdec::0001::4049dfdaa8fe": 9,
    "sbase::make_main.c::hasargs::0002::caccdf48eb91": 2,
    "sbase::make_parser.c::internal::0007::6720595969ae": 4,
    "sqlite::ext_fts3_fts3_tokenizer1.c::fts3_isalnum::0002::9b0f8eebf62b": 6,
    "sqlite::ext_misc_regexp.c::re_maxnfa::0011::403cd1ada2c2": 0,
    "sqlite::ext_misc_rot13.c::rot13::0001::29f43d50149a": 6,
    "sqlite::src_mem5.c::memsys5Log::0003::f8403d46bdea": 0,
    "sqlite::src_os_win.c::winMemRoundup::0005::7e0ed1b07591": 0,
    "sqlite::src_test_func.c::testHexChar::0001::9046f0b5e72e": 9,
    "sqlite::src_test_malloc.c::hexToInt::0006::50e837e0cf07": 6,
    "sqlite::src_util.c::pwr2to10::0010::f25b8f10dea3": 0,
    "xxHash::cli_xxhsum.c::charToHex::0005::cd1daff90d32": 9
  },
  "selected_function_count": 42,
  "total_char_literals": 126
}
```

## Seal

- Status: `sealed_after_exact_labeling`
- Seal manifest hash: `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`
- Final auditor invoked: `False`
- Prohibited final-method functions absent from execution log: `{"build_ordered_inputs": true, "fixture_neighbor_inputs": true, "interleave_inputs": true, "run_phase18_source_literal_char_policy": true, "source_literal_char_inputs": true}`
- Final-method imports/calls absent from runner AST: `{"forbidden_calls_absent": true, "forbidden_imports_absent": true}`
- Method-affecting hashes unchanged: `True`
- Natural and controlled strata separate: `True`
- Labels produced by complete exact-domain enumeration: `True`

## Tests Run

- `python -m py_compile analysis/decompile_faithfulness/holdout_acquisition.py`
- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze analysis.decompile_faithfulness.tests.test_submission_evidence_corrections analysis.decompile_faithfulness.tests.test_holdout_acquisition`

## Review Readiness

The complete holdout is ready for independent seal review if status is `sealed_after_exact_labeling` and the seal confirmations above remain true. No final-auditor detection results are included.
