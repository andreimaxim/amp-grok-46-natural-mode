Review this proposed Active Support change to `ActiveSupport::Inflector.parameterize`:

```diff
 def parameterize(string, separator: "-", preserve_case: false, locale: nil)
-  separator ||= ""
   parameterized_string = transliterate(string, locale: locale)
```

The PR claims the line is redundant because the keyword already defaults to `"-"`. Decide whether the claim and change are safe using this revision's implementation and tests. Trace the observable behavior of an explicitly supplied `separator: nil`, compare it with `separator: ""`, and identify the first downstream operation affected by the deletion. Check single-character and multi-character separator normalization and `preserve_case` for relevant regression scope. Return a concise PR verdict, evidence with path-and-line citations, and the smallest focused test cases you would request; do not write a patch.
