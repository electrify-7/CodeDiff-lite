#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
image="${COVDIFF_IMAGE:-covdiff-lite:testing}"
action="${1:-doctor}"
if (($#)); then shift; fi

if [[ "$action" == build ]]; then
  exec docker build --platform linux/amd64 -t "$image" "$project_root" "$@"
fi

image_id="$(docker image inspect --format '{{.Id}}' "$image")"
run_args=(run --rm --platform linux/amd64 --network none --memory 4g --cpus 4
  --user "$(id -u):$(id -g)" --mount "type=bind,source=$project_root,target=/work"
  --env "COVDIFF_IMAGE_ID=$image_id" --env "COVDIFF_IMAGE_REFERENCE=$image")
if [[ "$action" == test ]]; then
  exec docker "${run_args[@]}" "$image" python3 -m unittest discover -s tests -v "$@"
fi
exec docker "${run_args[@]}" "$image" python3 -m covdiff_lite "$action" "$@"
