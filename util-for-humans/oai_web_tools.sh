_internal__oai_fetch_url() {
    if (( $# != 2 )); then
        echo "usage: _internal__oai_fetch_url URL external_web_access" >&2
        return 2
    fi

    if [[ -z ${OPENAI_WEB_SEARCH_API_KEY:-} ]]; then
        echo "OPENAI_WEB_SEARCH_API_KEY is not set" >&2
        return 2
    fi

    local url=$1
    local external_web_access=$2
    local payload

    payload=$(
        jq -cn --arg url "$url" --argjson external_web_access "$external_web_access" '{
            model: "gpt-5.6-luna",
            tools: [{
                type: "web_search",
                search_context_size: "high",
                external_web_access: $external_web_access,
            }],
            tool_choice: "required",
            include: ["web_search_call.action.sources", "web_search_call.results"],
            input: (
                "Use the web tool to open this exact URL and return its contents. " +
                "Do not substitute another URL or perform a general search. URL: " +
                $url
            )
        }'
    ) || return

    curl --silent --show-error --fail-with-body \
        https://api.openai.com/v1/responses \
        -H "Authorization: Bearer ${OPENAI_WEB_SEARCH_API_KEY}" \
        -H "Content-Type: application/json" \
        --data-binary "$payload"
}

oai_fetch_url() {
    _internal__oai_fetch_url "$1" false
}

oai_fetch_url_live() {
    _internal__oai_fetch_url "$1" true
}

_internal__oai_search() {
    if (( $# != 2 )); then
        echo "usage: _internal__oai_search URL extra_instructions" >&2
        return 2
    fi

    if [[ -z ${OPENAI_WEB_SEARCH_API_KEY:-} ]]; then
        echo "OPENAI_WEB_SEARCH_API_KEY is not set" >&2
        return 2
    fi

    local query="$1"
    local extra_instructions="$1"
    local payload

    payload=$(
        jq -cn --arg query "$query" --arg extra_instructions "$extra_instructions" '{
            model: "gpt-5.6-luna",
            tools: [{
                type: "web_search",
                search_context_size: "high",
                external_web_access: false
            }],
            tool_choice: "required",
            include: ["web_search_call.action.sources", "web_search_call.results"],
            input: (
                "Use the web tool to perform this exact search: `\($query)`.\($extra_instructions) Reply with how many results you see."
            )
        }'
    ) || return

    curl --silent --show-error --fail-with-body \
        https://api.openai.com/v1/responses \
        -H "Authorization: Bearer ${OPENAI_WEB_SEARCH_API_KEY}" \
        -H "Content-Type: application/json" \
        --data-binary "$payload"
}

oai_search() {
    _internal__oai_search "$1" ""
}

oai_search_since() {
    _internal__oai_search "$1" "Search since $2 days ago."
}
