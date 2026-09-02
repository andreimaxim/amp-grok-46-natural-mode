#!/usr/bin/env bash
# Sparse-checkout the orb setup and plugin of both fixture repositories under .fixtures/
# so validate-experiment.py can confirm they match experiment.json and harness/.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
FIXTURE_COMMIT=$(python3 -c 'import json; print(json.load(open("experiment.json"))["fixture_commit"])')

fetch_fixture() {
	local name=$1
	local repository=$2
	local destination="$ROOT/.fixtures/$name"

	if [[ -d "$destination/.git" ]] &&
		[[ "$(git -C "$destination" rev-parse HEAD 2>/dev/null)" == "$FIXTURE_COMMIT" ]]; then
		return
	fi

	rm -rf "$destination"
	mkdir -p "$destination"
	git -C "$destination" init --quiet
	git -C "$destination" remote add origin "$repository"
	git -C "$destination" sparse-checkout init --cone
	git -C "$destination" sparse-checkout set .amp .agents
	git -C "$destination" fetch --quiet --depth=2 origin "$FIXTURE_COMMIT"
	git -C "$destination" checkout --quiet --detach FETCH_HEAD
}

fetch_fixture small "${GROK_SMALL_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-small}"
fetch_fixture large "${GROK_LARGE_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-large}"

echo "fixture checkouts are available under .fixtures/"
