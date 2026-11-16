#!/usr/bin/env bash
# Put the PoC-15 change into the local test repository as one commit.
#
# The change is the content of poc/poc-15/change/. It holds three planted
# problems (poc/poc-15/known-issues.json) for the cross-vendor review PoC.
# The script creates the branch poc-15-change from main in the test repo,
# commits the change with a fixed identity and date, and leaves that branch
# checked out. It writes only inside the test repo.
#
# Usage:
#   prepare-poc-15-change.sh          create the branch; stop if it exists
#   prepare-poc-15-change.sh --show   print base and head of an existing branch
#
# To go back to the initial content: git -C <testrepo> switch main

set -euo pipefail

readonly BRANCH="poc-15-change"
readonly MARKER=".poc-testrepo-marker"
readonly FIXED_DATE="2026-01-02T00:00:00Z"

mode="create"
case "${1:-}" in
  "") ;;
  --show) mode="show" ;;
  -h | --help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "unknown option: $1" >&2; exit 2 ;;
esac

# shellcheck disable=SC2046
unset $(git rev-parse --local-env-vars)
unset GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL

script_dir="$(cd "$(dirname "$0")" && pwd -P)"
change_dir="$script_dir/../poc-15/change"
target="$("$script_dir/create-test-repo.sh" --print-path)"

if [ -L "$target" ] || [ ! -f "$target/$MARKER" ] || [ ! -d "$target/.git" ]; then
  echo "test repository not found; create it first (see poc/README.md)" >&2
  exit 1
fi

export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_NOSYSTEM=1

if [ "$mode" = "show" ]; then
  echo "base: $(git -C "$target" rev-parse --verify main)"
  echo "head: $(git -C "$target" rev-parse --verify "$BRANCH")"
  exit 0
fi

if git -C "$target" rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
  echo "branch $BRANCH already exists; nothing changed" >&2
  exit 1
fi
if [ "$(git -C "$target" symbolic-ref --short HEAD)" != "main" ]; then
  echo "the test repo is not on main; nothing changed" >&2
  exit 1
fi
if [ -n "$(git -C "$target" status --porcelain=v1 --untracked-files=all --ignored)" ]; then
  echo "the test repo is not clean; nothing changed" >&2
  exit 1
fi

# Copy only the files that Git tracks (or has staged) in the change directory.
tracked="$(git -C "$change_dir" ls-files -- .)"
if [ -z "$tracked" ]; then
  echo "no tracked files in $change_dir; commit or stage the change first" >&2
  exit 1
fi

git -C "$target" switch --quiet -c "$BRANCH"
git -C "$change_dir" ls-files -z -- . | while IFS= read -r -d '' f; do
  mkdir -p "$target/$(dirname "$f")"
  cp "$change_dir/$f" "$target/$f"
done

export GIT_AUTHOR_DATE="$FIXED_DATE"
export GIT_COMMITTER_DATE="$FIXED_DATE"
git -C "$target" add --all --force
git -C "$target" commit --quiet --message "Add longest_line, count_file and word_frequencies"

echo "base: $(git -C "$target" rev-parse main)"
echo "head: $(git -C "$target" rev-parse HEAD)"
