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

	# Build the checkout in a scratch directory and move it into place only once it is complete,
	# so a failed fetch (the fixture repositories are private and orb setup may lack credentials
	# for them) leaves nothing behind.
	SCRATCH=$(mktemp -d "$ROOT/.fixtures/.$name.XXXXXX")
	git -C "$SCRATCH" init --quiet
	git -C "$SCRATCH" remote add origin "$repository"
	git -C "$SCRATCH" sparse-checkout init --cone
	git -C "$SCRATCH" sparse-checkout set .amp .agents
	git -C "$SCRATCH" fetch --quiet --depth=2 origin "$FIXTURE_COMMIT"
	git -C "$SCRATCH" checkout --quiet --detach FETCH_HEAD
	rm -rf "$destination"
	mv "$SCRATCH" "$destination"
	SCRATCH=
}

SCRATCH=
trap 'rm -rf "${SCRATCH:-/nonexistent}"' EXIT
mkdir -p "$ROOT/.fixtures"

fetch_fixture small "${GROK_SMALL_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-small}"
fetch_fixture large "${GROK_LARGE_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-large}"

echo "fixture checkouts are available under .fixtures/"
