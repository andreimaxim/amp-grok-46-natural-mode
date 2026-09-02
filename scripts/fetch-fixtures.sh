#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RAILS_REVISION=$(python3 -c 'import json; print(json.load(open("experiment.json"))["rails_revision"])')

fixture_commit() {
	python3 -c 'import json, sys; print(json.load(open("experiment.json"))["suites"][sys.argv[1]]["repository_commit"])' "$1"
}

fetch_fixture() {
	local name=$1
	local repository=$2
	local revision=$3
	local destination="$ROOT/.fixtures/$name"

	if [[ -d "$destination/.git" ]] &&
		[[ "$(git -C "$destination" rev-parse HEAD 2>/dev/null)" == "$revision" ]] &&
		git -C "$destination" cat-file -e "${RAILS_REVISION}^{commit}" 2>/dev/null; then
		return
	fi

	rm -rf "$destination"
	mkdir -p "$destination"
	git -C "$destination" init --quiet
	git -C "$destination" remote add origin "$repository"
	git -C "$destination" sparse-checkout init --cone
	git -C "$destination" sparse-checkout set .amp benchmark
	git -C "$destination" fetch --quiet --depth=1 origin "$revision"
	git -C "$destination" checkout --quiet --detach FETCH_HEAD
	git -C "$destination" fetch --quiet --depth=1 origin "$RAILS_REVISION"
}

cd "$ROOT"
fetch_fixture \
	small \
	"${GROK_SMALL_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-small}" \
	"$(fixture_commit small)"
fetch_fixture \
	large \
	"${GROK_LARGE_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-large}" \
	"$(fixture_commit large)"

echo "fixture manifests and scenarios are available under .fixtures/"
