#!/usr/bin/env bash
# Archive every Amp thread a generation created, once its results are committed.
#
#   scripts/archive-generation-threads.sh <GNNNN> [extra-thread-id ...]
#
# Collects thread_id, superseded_thread_ids and judge_thread_id from every
# runs/<GNNNN>/**/*.json record, adds the extra IDs given on the command line
# (coordinator threads, which no record names), and archives each with
# `amp threads archive`. Safe to rerun: already archived threads are skipped.
set -euo pipefail

if [[ $# -lt 1 ]]; then
	echo "usage: $0 <GNNNN> [extra-thread-id ...]" >&2
	exit 2
fi

generation=$1
shift
run_dir="runs/$generation"

if [[ ! -d "$run_dir" ]]; then
	echo "$run_dir does not exist" >&2
	exit 1
fi

mapfile -t threads < <(
	{
		find "$run_dir" -name '*.json' ! -name 'summary.json' -print0 |
			xargs -0 jq -r '[.thread_id?, .judge_thread_id?, (.superseded_thread_ids? // [])[]] | .[] | select(. != null)'
		printf '%s\n' "$@"
	} | rg '^T-[0-9a-f-]+$' | sort -u
)

if [[ ${#threads[@]} -eq 0 ]]; then
	echo "no thread IDs found for $generation" >&2
	exit 1
fi

# `amp threads archive` fails transiently now and then; retry a few times
# before giving up on a thread.
archive_thread() {
	local thread=$1 attempt
	for attempt in 1 2 3 4; do
		if amp threads archive "$thread" >/dev/null 2>&1; then
			return 0
		fi
		sleep $((attempt * 5))
	done
	return 1
}

archived=0
failed=()
for thread in "${threads[@]}"; do
	if archive_thread "$thread"; then
		archived=$((archived + 1))
	else
		failed+=("$thread")
	fi
done

echo "$generation: archived $archived of ${#threads[@]} threads"
if [[ ${#failed[@]} -gt 0 ]]; then
	printf 'failed: %s\n' "${failed[@]}" >&2
	exit 1
fi
