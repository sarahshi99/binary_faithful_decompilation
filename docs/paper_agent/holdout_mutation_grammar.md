# Holdout Mutation Grammar

This grammar is sealed before semantic labels or final-auditor outputs are inspected.

Families:

1. comparison-operator replacement: replace the first eligible `==`, `!=`, `<`, `<=`, `>`, or `>=` with a deterministic paired operator.
2. integer or character constant +/- 1: increment the first numeric scalar constant by one when the result remains syntactically valid.
3. branch-condition negation: wrap the first simple `if` predicate in `!(...)`.
4. off-by-one arithmetic mutation: covered by constant +/- 1 and return perturbation for this sealed implementation.
5. return-value perturbation: add one to the first return expression.
6. argument substitution or swap: for two same-type arguments, swap first body occurrences.
7. deletion or inversion of one conditional arm: represented by first simple branch-condition negation in this implementation.
8. fixture-overfit construction: emit a deterministic if-chain over sealed fixtures and return zero otherwise.

Eligibility requires scalar return/arguments, syntactic transformation success, and candidate compile handling during exact labeling. At most two controlled candidates are selected per function using the committed mutation seed. Failed compilation is `non_evaluable`, not semantic wrong.
