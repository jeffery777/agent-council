#!/usr/bin/env bash
# Create or rebuild the local test repository for the M1 PoC.
#
# The test repository is a sibling of the main checkout of this project:
#   <repo>/../agent-council-poc-testrepo
# It exists only on the local machine and gets no remote.
# This script writes outside this repository. The maintainer must agree before
# each run that creates or recreates the test repo (M1 PoC plan, rule 7).
#
# Usage:
#   create-test-repo.sh               create; stop if the directory exists
#   create-test-repo.sh --recreate    delete the existing test repo, then create
#   create-test-repo.sh --print-path  print the target path and write nothing

set -euo pipefail

readonly TEST_REPO_NAME="agent-council-poc-testrepo"
readonly MARKER=".poc-testrepo-marker"
readonly FIXED_DATE="2026-01-01T00:00:00Z"

usage() {
  sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
}

mode="create"
case "${1:-}" in
  "") ;;
  --recreate) mode="recreate" ;;
  --print-path) mode="print" ;;
  -h | --help) usage; exit 0 ;;
  *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then
  echo "too many arguments" >&2
  exit 2
fi

# Git variables inherited from the caller (for example from a hook) must not
# redirect this script to another repository, index or identity.
# shellcheck disable=SC2046
unset $(git rev-parse --local-env-vars)
unset GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL

script_dir="$(cd "$(dirname "$0")" && pwd -P)"
fixture_dir="$script_dir/../fixtures/test-repo"

# The main checkout owns the common .git directory, also when this script runs
# from a linked worktree.
common_git_dir="$(cd "$script_dir" && git rev-parse --path-format=absolute --git-common-dir)"
main_checkout="$(dirname "$common_git_dir")"
target="$(dirname "$main_checkout")/$TEST_REPO_NAME"

if [ "$mode" = "print" ]; then
  echo "$target"
  exit 0
fi

if [ ! -f "$fixture_dir/$MARKER" ]; then
  echo "fixture not found: $fixture_dir" >&2
  exit 1
fi

if [ -e "$target" ] || [ -L "$target" ]; then
  if [ "$mode" != "recreate" ]; then
    echo "already exists: $target" >&2
    echo "nothing changed; use --recreate to delete and rebuild it" >&2
    exit 1
  fi
  # Delete only a real directory that this script created.
  if [ -L "$target" ] || [ ! -d "$target" ] || [ ! -f "$target/$MARKER" ] || [ ! -d "$target/.git" ]; then
    echo "refusing to delete: $target is not a test repo made by this script" >&2
    exit 1
  fi
  rm -rf "$target"
fi

# Copy only the files that Git tracks in the fixture directory. A stray local
# file there (for example .DS_Store or .env) must not reach the test repo.
tracked="$(git -C "$fixture_dir" ls-files -- .)"
if [ -z "$tracked" ]; then
  echo "no tracked files in $fixture_dir; commit or stage the fixture first" >&2
  exit 1
fi

mkdir "$target"
git -C "$fixture_dir" ls-files -z -- . | while IFS= read -r -d '' f; do
  mkdir -p "$target/$(dirname "$f")"
  cp "$fixture_dir/$f" "$target/$f"
done

# Do not use the user's or the system's Git configuration files while building
# the test repo (templates, hooks, signing, default branch).
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_DATE="$FIXED_DATE"
export GIT_COMMITTER_DATE="$FIXED_DATE"

git -C "$target" init --quiet --template= --initial-branch=main
# A placeholder identity, stored only in the test repo.
git -C "$target" config user.name "PoC Test"
git -C "$target" config user.email "poc-test@example.invalid"
git -C "$target" config commit.gpgsign false
# --force: the user's default excludes file must not drop a fixture file.
git -C "$target" add --all --force
git -C "$target" commit --quiet --message "Initial content of the PoC test repository"

if [ -n "$(git -C "$target" remote)" ]; then
  echo "unexpected remote in $target" >&2
  exit 1
fi

echo "created: $target"
echo "HEAD: $(git -C "$target" rev-parse HEAD)"
