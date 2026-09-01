#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

fetch_fixture() {
	local name=$1
	local repository=$2
	local revision=$3
	local destination="$ROOT/.fixtures/$name"

	if [[ -d "$destination/.git" ]] &&
		[[ "$(git -C "$destination" rev-parse HEAD)" == "$revision" ]]; then
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
}

fetch_fixture \
	small \
	"${GROK_SMALL_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-small}" \
	3e02d92e757a0c857ee2b706b752ad312a924412
fetch_fixture \
	large \
	"${GROK_LARGE_REPOSITORY:-https://github.com/andreimaxim/rails-for-grok-large}" \
	caae5b024eba4ab2d1f9c7400784d9fe99eed726

echo "fixture manifests and scenarios are available under .fixtures/"
