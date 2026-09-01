#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RAILS_REVISION=d59d106f94dcb7f8e748545c0ccf8a276d20f590

fetch_fixture() {
	local name=$1
	local repository=$2
	local revision=$3
	local destination="$ROOT/.fixtures/$name"

	if [[ -d "$destination/.git" ]] &&
		[[ "$(git -C "$destination" rev-parse HEAD)" == "$revision" ]] &&
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

fetch_fixture \
	small \
	"${GROK_SMALL_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-small}" \
	d578be2099521a952ffdb950451c8e9ffa3996c5
fetch_fixture \
	large \
	"${GROK_LARGE_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-large}" \
	79ecfcdc4e39afbda4cd8233181b07c2b211ada2

echo "fixture manifests and scenarios are available under .fixtures/"
