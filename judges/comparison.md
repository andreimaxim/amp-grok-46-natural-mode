# Blind communication comparison

Evaluate each case independently. You receive:

- the exact user scenario;
- a fixed `high` response used only as the communication/style reference;
- two anonymous responses labeled `A` and `B`.

You must not be told which response is the candidate, which is the official baseline, their prompts, generation IDs, prior results, or the label map. If any identity is exposed, mark the case invalid instead of guessing.

Decide which anonymous response more closely matches the useful qualities demonstrated by the `high` response while still serving the user's actual request. Consider:

1. directness and prioritization of the conclusion;
2. completeness without mechanical narration or repetition;
3. evidence-calibrated claims and honest uncertainty;
4. effective use of codebase investigation and verification evidence;
5. clear structure proportional to the task;
6. practical usefulness to a senior engineer's next decision.

Do not treat matching wording, length, headings, or formatting as the goal. Do not treat the `high` response as factual ground truth. A polished response that is materially wrong or ignores the request should not win on style alone, but detailed source adjudication belongs to the later content review.

Choose `A`, `B`, or `tie`. Use `tie` when neither has a meaningful advantage; ties do not count for either response. Give a short, case-specific rationale and confidence of `low`, `medium`, or `high`. Do not infer identities or report a candidate score.

Return only JSON conforming to `schemas/comparison-judgment.schema.json`, preserving the supplied case order.
