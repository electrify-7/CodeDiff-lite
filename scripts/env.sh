#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
action="${1:-doctor}"
if (($#)); then shift; fi
default_image=covdiff-lite:testing
case "$action" in
  pipeline|empirical|plots|experiment|test) default_image=covdiff-lite:reporting ;;
esac
image="${COVDIFF_IMAGE:-$default_image}"

if [[ "$action" == build ]]; then
  exec docker build --platform linux/amd64 -t "$image" "$project_root" "$@"
fi
if [[ "$action" == build-reporting ]]; then
  exec docker build --platform linux/amd64 -f "$project_root/Dockerfile.reporting" \
    --build-arg "BASE_IMAGE=${COVDIFF_BASE_IMAGE:-covdiff-lite:testing}" \
    -t "${COVDIFF_IMAGE:-covdiff-lite:reporting}" "$project_root" "$@"
fi

image_id="$(docker image inspect --format '{{.Id}}' "$image")"
run_args=(run --rm --platform linux/amd64 --network none --memory 4g --cpus 4
  --user "$(id -u):$(id -g)" --mount "type=bind,source=$project_root,target=/work"
  --env "COVDIFF_IMAGE_ID=$image_id" --env "COVDIFF_IMAGE_REFERENCE=$image")
if [[ "$action" == test ]]; then
  exec docker "${run_args[@]}" "$image" python3 -m unittest discover -s tests -v "$@"
fi
exec docker "${run_args[@]}" "$image" python3 -m covdiff_lite "$action" "$@"
