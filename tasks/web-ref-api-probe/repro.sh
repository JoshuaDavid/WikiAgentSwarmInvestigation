#!/usr/bin/env bash
# Requires curl, jq, and OPENAI_WEB_SEARCH_API_KEY. Makes 4 Responses API calls.
set +x
set -euo pipefail
: "${OPENAI_WEB_SEARCH_API_KEY:?Set OPENAI_WEB_SEARCH_API_KEY first}"
for cmd in curl jq; do command -v "$cmd" >/dev/null; done
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/web-ref-repro.XXXXXX")
printf 'Request/response logs: %s\n' "$run_dir"

jq -n --arg model "${MODEL:-gpt-5.5}" '{
  model: $model, tools: [{type: "web_search"}], store: true,
  reasoning: {effort: "low"}, max_output_tokens: 2000,
  include: ["web_search_call.results"],
  instructions: "Follow the requested web calls exactly. Report actual tool errors. Never replace a requested opaque ref with a URL. Do not search or retry."
}' > "$run_dir/base.json"

# Read additional request fields from stdin. Keep the key out of logs and argv.
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

# 1. Follow three reference/link hops within one API response.
jq -n '{max_tool_calls: 4, input:
  "Open https://developers.openai.com/api/docs/guides/tools-web-search. Then make exactly THREE sequential clicks using the preceding page ref and an actually visible numbered link. Each click must visit a different, not-yet-visited page on developers.openai.com. Four web calls total: open URL, click, click, click. Do not substitute URL opens for clicks. Finish by reporting the final page URL and ref."
}' | respond browse

jq '[.output[] | select(.type == "web_search_call")]' \
  "$run_dir/browse.response.json" > "$run_dir/pages.json"
jq -e 'length == 4 and all(.[]; (.results | length) > 0)
  and ([.[].results[0].url] | unique | length) == 4
  and all(.[1:][]; .results[0].snippet | contains("Source: click("))' \
  "$run_dir/pages.json" >/dev/null
# results[].url is the destination; action.url can be the page clicked FROM.
jq -er '.[-1].results[0].url' "$run_dir/pages.json" > "$run_dir/url.txt"
old_ref=$(jq -er '.[-1].results[0].snippet | capture("(?<ref>turn[0-9]+view[0-9]+)").ref' "$run_dir/pages.json")
previous_id=$(jq -er '.id' "$run_dir/browse.response.json")

# 2. Negative control: even preserved conversation context loses the old ref.
jq -n --arg previous "$previous_id" --arg ref "$old_ref" '{
  previous_response_id: $previous, max_tool_calls: 1,
  input: ("Open exactly the opaque reference " + $ref + ". Pass the ref itself, not its URL. Make one web call, then report success or the exact error.")
}' | respond old-ref
jq -e '[.output[] | select(.type == "web_search_call")] |
  length == 1 and .[0].action.type == "open_page"
  and (.[0].results | length) == 0 and (.[0].action.url // "") == ""' \
  "$run_dir/old-ref.response.json" >/dev/null

# 3. Fresh conversation: the user names a file, without supplying its URL.
reader='{"type":"function","name":"read_url_file","description":"Read url.txt from disk.","strict":true,"parameters":{"type":"object","properties":{},"required":[],"additionalProperties":false}}'
jq -n --argjson reader "$reader" '{
  tools: [$reader], tool_choice: {type: "function", name: "read_url_file"},
  input: "Read url.txt using read_url_file. When its contents arrive, open the URL with the web tool, then open the fresh ref returned by that open. Exactly two web calls after reading the file. Report success or errors."
}' | respond read-file
read_id=$(jq -er '.id' "$run_dir/read-file.response.json")
call_id=$(jq -er '[.output[] | select(.type == "function_call" and .name == "read_url_file")] |
  if length == 1 then .[0].call_id else error("Expected one file-read call") end' "$run_dir/read-file.response.json")

# 4. Execute the model's file-read call. The URL enters ONLY as tool output.
jq -n --arg previous "$read_id" --arg call "$call_id" \
  --argjson reader "$reader" --rawfile saved "$run_dir/url.txt" '{
  previous_response_id: $previous, max_tool_calls: 2,
  tools: [{type: "web_search"}, $reader],
  input: [{type: "function_call_output", call_id: $call, output: ($saved | rtrimstr("\n"))}]
}' | respond resume

jq -e --rawfile saved "$run_dir/url.txt" '
  [.output[] | select(.type == "web_search_call")] as $calls |
  ($saved | rtrimstr("\n")) as $url |
  ($calls[0].results[0].snippet | capture("(?<ref>turn[0-9]+view[0-9]+)").ref) as $fresh |
  ($calls | length) == 2
  and all($calls[]; .action.type == "open_page" and .results[0].url == $url)
  and ($calls[0].results[0].snippet | contains("\"ref_id\":\"" + $url + "\""))
  and ($calls[1].results[0].snippet | contains("\"ref_id\":\"" + $fresh + "\""))
' "$run_dir/resume.response.json" >/dev/null

printf '\nPASS: old ref failed; URL supplied ONLY by file-read tool opened successfully; fresh ref worked.\nSaved URL: '
cat "$run_dir/url.txt"
printf '\nOld-ref error reported by model:\n'
jq -r '.output[] | select(.type == "message") | .content[] | select(.type == "output_text") | .text' \
  "$run_dir/old-ref.response.json"
