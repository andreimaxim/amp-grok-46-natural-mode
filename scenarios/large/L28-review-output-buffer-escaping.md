Review a proposed Action View change whose author claims `ActionView::OutputBuffer#safe_concat` should escape ordinary strings to make capture safer:

```diff
diff --git a/actionview/lib/action_view/buffers.rb b/actionview/lib/action_view/buffers.rb
@@
   def safe_concat(value)
-    @raw_buffer << value
+    @raw_buffer << ERB::Util.html_escape(value)
     self
   end
```

Assess the claim against the contracts of `OutputBuffer#<<`, `#safe_concat`, `#capture`, `RawOutputBuffer`, and `ActionView::Helpers::CaptureHelper#capture`. Trace relevant source and tests, including observable output for an unsafe string, an `html_safe` string, a nested capture that writes and returns a value, `nil`, and a value already represented by an output buffer. Return a PR-style review with severity-ranked findings, exact evidence, compatibility/security implications, and narrowly targeted test cases. Do not provide a replacement implementation unless needed to make a specific finding understandable.
