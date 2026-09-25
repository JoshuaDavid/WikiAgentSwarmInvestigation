#!/usr/bin/env bash
# Exact two-user-message test. Requires curl, jq, OPENAI_WEB_SEARCH_API_KEY.
# Three API requests: one shared first turn, then two continuation variants.
set +x
set -euo pipefail
: "${OPENAI_WEB_SEARCH_API_KEY:?Set OPENAI_WEB_SEARCH_API_KEY first}"
for cmd in curl jq; do command -v "$cmd" >/dev/null; done
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/one-click-next-turn.XXXXXX")
printf 'Logs: %s\n' "$run_dir"
jq -n --arg model "${MODEL:-gpt-5.5}" '{
  model: $model, tools: [{type: "web_search"}], store: true,
  reasoning: {effort: "low"}, max_output_tokens: 2000,
  include: ["web_search_call.results", "reasoning.encrypted_content"],
  instructions: "Execute the requested web calls exactly. Report actual tool results and errors. Stop after the requested calls; do not search or use workarounds."
}' > "$run_dir/base.json"
respond() {
  local label=$1
  jq -s '.[0] + .[1]' "$run_dir/base.json" - > "$run_dir/$label.request.json"
  printf 'Running %s...\n' "$label" >&2
  curl --silent --show-error --fail-with-body --connect-timeout 20 --max-time 180 \
    https://api.openai.com/v1/responses \
    --header @<(printf 'Authorization: Bearer %s\n' "$OPENAI_WEB_SEARCH_API_KEY") \
    --header 'Content-Type: application/json' \
    --data-binary "@$run_dir/$label.request.json" > "$run_dir/$label.response.json"
  jq -e '.status == "completed"' "$run_dir/$label.response.json" >/dev/null || {
    cat "$run_dir/$label.response.json" >&2; return 1;
  }
}

# User message 1: the destination URL is unknown and not supplied to the model.
jq -n '{max_tool_calls: 2, input:
  "Open https://joshuadavid.github.io/swarm-maze/pages/29135.html. Inspect the returned page and click its first numbered link to a different page in the same maze, using the returned page reference and numbered link ID. Exactly two sequential web calls: open, then click. After the click, note the destination page URL from the tool result in your final answer, along with its title. Do not search or open additional pages."
}' | respond first
jq '[.output[] | select(.type == "web_search_call")]' \
  "$run_dir/first.response.json" > "$run_dir/pages.json"
jq -e 'length == 2 and all(.[]; (.results | length) > 0)
  and .[0].action.type == "open_page"
  and .[0].results[0].url != .[1].results[0].url
  and (.[1].results[0].snippet | contains("Source: click("))' \
  "$run_dir/pages.json" >/dev/null
destination=$(jq -er '.[1].results[0].url' "$run_dir/pages.json")
jq -e --arg url "$destination" '
  [.output[] | select(.type == "message") | .content[] |
   select(.type == "output_text") | .text] | join("\n") | contains($url)
' "$run_dir/first.response.json" >/dev/null

# User message 2 is identical in both branches and contains no URL.
followup='Open the URL of the page you reached by clicking in the previous turn. Use the destination URL you noted, not an opaque reference. Make exactly one open call. Do not search, click, or retry. Report the attempted URL and either success or the exact tool error.'
jq -n --slurpfile first "$run_dir/first.response.json" --arg input "$followup" '{
  previous_response_id: $first[0].id, max_tool_calls: 1, input: $input
}' | respond previous
jq -n --slurpfile first "$run_dir/first.response.json" \
  --slurpfile original "$run_dir/first.request.json" --arg input "$followup" '{
  max_tool_calls: 1,
  input: ([{role: "user", content: $original[0].input}] + $first[0].output +
          [{role: "user", content: $input}])
}' | respond replay

# Verify that the model attempted the actual destination URL, not the old ref.
for label in previous replay; do
  jq -e --arg url "$destination" '
    [.output[] | select(.type == "web_search_call")] |
    length == 1 and .[0].action.type == "open_page" and .[0].action.url == $url
  ' "$run_dir/$label.response.json" >/dev/null
  jq --arg mode "$label" --arg destination "$destination" '{
    mode: $mode, model, destination: $destination,
    result_count: ([.output[] | select(.type == "web_search_call") | .results[]] | length),
    assistant_report: ([.output[] | select(.type == "message") | .content[] |
                       select(.type == "output_text") | .text] | join("\n"))
  }' "$run_dir/$label.response.json"
done
