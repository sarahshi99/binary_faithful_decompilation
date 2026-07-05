# Prospective Natural LLM API Compatibility Note

Generated: 2026-07-05

This note records a pre-response provider compatibility issue encountered after
the Phase 1h preregistration commit and before any model candidate response was
accepted, parsed, compiled, labeled, fixture-replayed, or evaluated.

The preregistration specified deterministic generation with `temperature=0` and
`top_p=1` where the API supports it. The configured Responses-compatible relay
returned HTTP 400 for the first attempted request with:

`Unsupported parameter: top_p`

No candidate response was stored for that request. The only generated artifact
was the prompt payload for the first matrix item, and it contains no model
output.

Compatibility decision:

- retain requested model `gpt-5.5`;
- retain `temperature=0`;
- retain `max_output_tokens=2048`;
- omit the explicit `top_p=1` field from the API payload because the provider
  rejects that explicit default;
- record this omission in generation metadata and seals;
- do not change prompts, request matrix, candidate selection, parsing,
  normalization, labeling, final-policy evaluation, or libFuzzer configuration.

This is not a result-driven change: it happened before candidate generation,
labels, fixtures, final-auditor results, or libFuzzer results existed for the
natural LLM stratum.
