#!/usr/bin/env bash
# Install or remove the PoC-13 hooks in the local test repository.
#
# Writes only inside the test repository:
#   .claude/hooks/poc13-hook.py, .claude/hooks/poc13-channel.py,
#   .claude/settings.local.json, .mcp.json (channel profile only), .poc-13/
# and lists these paths in the test repo's .git/info/exclude.
#
# Usage:
#   prepare-poc-13.sh inject   install the "hooks inject the inbox" profile
#   prepare-poc-13.sh rewake   install the asyncRewake profile
#   prepare-poc-13.sh channel  install the custom channel profile
#   prepare-poc-13.sh remove   remove the hooks and settings; keep .poc-13/
#
# Close the session under test before switching profiles or removing them.

set -euo pipefail

readonly MARKER=".poc-testrepo-marker"
profile="${1:-}"
case "$profile" in
  inject | rewake | channel | remove) ;;
  *) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2 ;;
esac
if [ "$#" -ne 1 ]; then
  echo "too many arguments" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "$0")" && pwd -P)"
source_dir="$script_dir/../poc-13"
target="$("$script_dir/create-test-repo.sh" --print-path)"

if [ ! -f "$target/$MARKER" ] || [ ! -d "$target/.git" ]; then
  echo "test repo not found: run create-test-repo.sh first" >&2
  exit 1
fi

settings="$target/.claude/settings.local.json"
hook="$target/.claude/hooks/poc13-hook.py"
channel="$target/.claude/hooks/poc13-channel.py"
mcp="$target/.mcp.json"

# settings.local.json and .mcp.json are removed or replaced only when this
# script wrote them.
ours() { [ ! -e "$1" ] || grep -q "$2" "$1"; }
if ! ours "$settings" 'poc13-hook.py' || ! ours "$mcp" 'poc13-channel.py'; then
  echo "settings.local.json or .mcp.json exists and is not from this script; not touching anything" >&2
  exit 1
fi

if [ "$profile" = "remove" ]; then
  rm -f "$settings" "$hook" "$channel" "$mcp" "$target/.poc-13/profile"
  echo "removed the PoC-13 hooks; .poc-13/ is kept"
  exit 0
fi

rm -f "$target/.poc-13/profile"  # written again only after a complete install
mkdir -p "$target/.claude/hooks" "$target/.poc-13/inbox" "$target/.poc-13/rewake" \
  "$target/.poc-13/channel" "$target/.poc-13/delivered"
cp "$source_dir/hook.py" "$hook"
cp "$source_dir/settings.$profile.json" "$settings"
# Only the channel profile starts the MCP server.
rm -f "$mcp" "$channel"
if [ "$profile" = "channel" ]; then
  cp "$source_dir/channel.py" "$channel"
  cp "$source_dir/mcp.channel.json" "$mcp"
fi

exclude="$target/.git/info/exclude"
mkdir -p "$(dirname "$exclude")"
for entry in "/.claude/" "/.poc-13/" "/.mcp.json"; do
  grep -qxF "$entry" "$exclude" 2>/dev/null || echo "$entry" >> "$exclude"
done

echo "$profile" > "$target/.poc-13/profile"
echo "installed profile: $profile"
