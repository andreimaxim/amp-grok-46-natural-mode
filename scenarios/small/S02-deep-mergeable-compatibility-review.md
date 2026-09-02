Review this proposed simplification to `ActiveSupport::DeepMergeable#deep_merge!` and write the PR comment you would leave:

```diff
- if this_val.is_a?(DeepMergeable) && this_val.deep_merge?(other_val)
+ if this_val.is_a?(DeepMergeable) && other_val.is_a?(DeepMergeable)
```

Inspect the implementation and tests. Focus on compatibility ownership, custom `DeepMergeable` classes, block fallback, and observable mutation and return behavior. Do not edit files.
