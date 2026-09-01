# Post-comparison content regression review

The blind comparison decisions for these cases have already been persisted. You now receive the label map identifying the candidate and official-baseline responses. Do not revise the earlier preference decisions.

Review correctness against the pinned Rails checkout and the user's exact request. The fixed `high` response is useful evidence but is not authoritative. Verify disputed or consequential claims directly in source, tests, or focused executed checks.

A **material error** is one that could change the user's implementation, review, behavioral contract, or confidence: an incorrect API/flow claim, missed required behavior, unsafe recommendation, invented verification, or a conclusion unsupported by the available evidence. Stylistic weaknesses and harmless omissions are not material errors.

Classify each verified material issue as:

- `candidate_only`: present in the candidate but not the official baseline;
- `shared`: present in both candidate and baseline;
- `baseline_only`: present only in the baseline.

Do not classify a disagreement merely because another response phrases it differently. Every material finding must include a concise explanation and source path/line range or executed command evidence. If evidence is insufficient, record uncertainty rather than an error.

Return only JSON conforming to `schemas/content-review.schema.json`. The experiment's correctness gate uses the number of `candidate_only` material findings; shared and baseline-only findings remain recorded for diagnosis.
