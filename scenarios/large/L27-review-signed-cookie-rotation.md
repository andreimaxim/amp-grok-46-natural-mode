Review a proposed Action Pack change whose author claims it safely avoids unnecessary signed-cookie rewrites after key rotation:

```diff
diff --git a/actionpack/lib/action_dispatch/middleware/cookies.rb b/actionpack/lib/action_dispatch/middleware/cookies.rb
@@
-          super(name, data, force_reserialize: rotated)
+          super(name, data, force_reserialize: false)
```

Determine whether the claim and patch are correct at this revision. Trace signed jar reads, message-verifier rotation, serializer/digest upgrades, metadata expiry, and writes through the cookie jar. Use `actionpack/test/dispatch/cookies_test.rb` and any directly relevant Active Support message tests to establish observable behavior for a current signature, an old secret, an old digest or serializer, an expired cookie, and a tampered cookie. Return a PR-style review with findings ordered by severity, precise source/test evidence, and focused tests the proposed change would need; do not rewrite the patch wholesale.
