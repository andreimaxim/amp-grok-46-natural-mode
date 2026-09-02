#!/usr/bin/env bash
# Export an Amp thread as Markdown without the front matter that names its agent mode.
#
#   scripts/export-thread.sh <thread-id> <output-path>
set -euo pipefail

if [[ $# -ne 2 ]]; then
	echo "usage: $0 <thread-id> <output-path>" >&2
	exit 2
fi

thread=$1
output=$2

mkdir -p "$(dirname "$output")"
amp threads markdown "$thread" | awk '
	NR == 1 && $0 == "---" { skipping = 1; next }
	skipping && $0 == "---" { skipping = 0; next }
	skipping { next }
	!started && !NF { next }
	{ started = 1; print }
' >"$output"

if [[ ! -s "$output" ]]; then
	echo "thread $thread exported an empty transcript" >&2
	exit 1
fi
