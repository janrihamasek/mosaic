#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: import_github_project.sh --owner <github-username> [--roadmap <relative-path>]

Automates creation (or update) of a GitHub Projects table from roadmap.json.

Options:
  --owner     GitHub username or organization that will own the project (required)
  --roadmap   Path to roadmap JSON file relative to the repository root
              (default: mosaic_prototype/scripts/roadmap.json)
  -h, --help  Show this help message
EOF
}

OWNER=""
ROADMAP_RELATIVE="mosaic_prototype/scripts/roadmap.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner)
      [[ $# -lt 2 ]] && { echo "Error: --owner requires a value." >&2; exit 1; }
      OWNER="$2"
      shift 2
      ;;
    --roadmap)
      [[ $# -lt 2 ]] && { echo "Error: --roadmap requires a value." >&2; exit 1; }
      ROADMAP_RELATIVE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$OWNER" ]]; then
  echo "Error: --owner is required." >&2
  usage
  exit 1
fi

for cmd in gh jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: Required command '$cmd' is not installed or not on PATH." >&2
    exit 1
  fi
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROADMAP_PATH="$REPO_ROOT/$ROADMAP_RELATIVE"

if [[ ! -f "$ROADMAP_PATH" ]]; then
  echo "Error: roadmap file not found at '$ROADMAP_PATH'." >&2
  exit 1
fi

PROJECT_TITLE="$(jq -r '.project_title // empty' "$ROADMAP_PATH")"
if [[ -z "$PROJECT_TITLE" ]]; then
  echo "Error: project_title missing in '$ROADMAP_PATH'." >&2
  exit 1
fi

fetch_project_number() {
  gh project list --owner "$OWNER" --format json --limit 200 \
    | jq -r --arg title "$PROJECT_TITLE" '.projects[]? | select(.title == $title) | .number' \
    | head -n1
}

PROJECT_NUMBER="$(fetch_project_number)"

if [[ -n "$PROJECT_NUMBER" ]]; then
  echo "Project '$PROJECT_TITLE' already exists as project #$PROJECT_NUMBER. Skipping creation."
else
  echo "Creating project '$PROJECT_TITLE' for owner '$OWNER'..."
  gh project create --title "$PROJECT_TITLE" --owner "$OWNER" --format json >/dev/null
  PROJECT_NUMBER="$(fetch_project_number)"
  if [[ -z "$PROJECT_NUMBER" ]]; then
    echo "Error: Unable to resolve project number after creation." >&2
    exit 1
  fi
fi

AREA_OPTIONS=()
PRIORITY_OPTIONS=()
STATUS_OPTIONS=()

mapfile -t AREA_OPTIONS < <(jq -r '.items | map(.Area) | unique[]?' "$ROADMAP_PATH")
mapfile -t PRIORITY_OPTIONS < <(jq -r '.items | map(.Priority) | unique[]?' "$ROADMAP_PATH")
mapfile -t STATUS_OPTIONS < <(jq -r '.items | map(.Status) | unique[]?' "$ROADMAP_PATH")

area_options_csv=""
priority_options_csv=""
status_options_csv=""

if (( ${#AREA_OPTIONS[@]} )); then
  area_options_csv="$(IFS=','; echo "${AREA_OPTIONS[*]}")"
fi
if (( ${#PRIORITY_OPTIONS[@]} )); then
  priority_options_csv="$(IFS=','; echo "${PRIORITY_OPTIONS[*]}")"
fi
if (( ${#STATUS_OPTIONS[@]} )); then
  status_options_csv="$(IFS=','; echo "${STATUS_OPTIONS[*]}")"
fi

refresh_field_cache() {
  gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json
}

FIELD_CACHE="$(refresh_field_cache)"

ensure_field() {
  local name="$1"
  local type="$2"
  local options="${3:-}"

  local existing_id
  existing_id="$(echo "$FIELD_CACHE" | jq -r --arg name "$name" '.fields[]? | select(.name == $name) | .id' | head -n1)"
  if [[ -n "$existing_id" ]]; then
    echo "Field '$name' already exists (id: $existing_id)."
    return
  fi

  local cmd=(gh project field-create "$PROJECT_NUMBER" --owner "$OWNER" --name "$name" --data-type "$type")
  if [[ "$type" == "SINGLE_SELECT" && -n "$options" ]]; then
    cmd+=(--single-select-options "$options")
  fi

  "${cmd[@]}"
  FIELD_CACHE="$(refresh_field_cache)"
}

ensure_field "Area" "SINGLE_SELECT" "$area_options_csv"
ensure_field "Estimate" "NUMBER"
ensure_field "Priority" "SINGLE_SELECT" "$priority_options_csv"
ensure_field "Status" "SINGLE_SELECT" "$status_options_csv"

existing_titles=()
if existing_json="$(gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" --format json --limit 200 2>/dev/null)"; then
  mapfile -t existing_titles < <(echo "$existing_json" | jq -r '.items[]? | .title')
fi

contains_title() {
  local needle="$1"
  for title in "${existing_titles[@]}"; do
    if [[ "$title" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

echo "Syncing roadmap items into project #$PROJECT_NUMBER..."

while IFS= read -r item; do
  title="$(jq -r '.Title' <<<"$item")"
  area="$(jq -r '.Area // empty' <<<"$item")"
  estimate="$(jq -r '.Estimate // empty' <<<"$item")"
  priority="$(jq -r '.Priority // empty' <<<"$item")"
  status="$(jq -r '.Status // empty' <<<"$item")"

  if contains_title "$title"; then
    echo "Skipping existing item: $title"
    continue
  fi

  args=(gh project item-create "$PROJECT_NUMBER" --owner "$OWNER" --title "$title")
  [[ -n "$area" ]] && args+=(--field "Area=$area")
  [[ -n "$estimate" ]] && args+=(--field "Estimate=$estimate")
  [[ -n "$priority" ]] && args+=(--field "Priority=$priority")
  [[ -n "$status" ]] && args+=(--field "Status=$status")

  "${args[@]}"
  existing_titles+=("$title")
done < <(jq -c '.items[]' "$ROADMAP_PATH")

echo
echo "Project '$PROJECT_TITLE' (#$PROJECT_NUMBER) has been updated with roadmap items."
echo "Current items in the project:"
gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" --limit 200
