"""Exact, model-facing error text presets; these are custom function outputs."""

PRESETS = {
    'cache_miss': {
        'label': 'Cache miss',
        'template': 'Failed to fetch {url}: Cache miss',
        'source': 'Existing playground cache-miss response',
    },
    'unsafe_non_retryable': {
        'label': 'Not safe · non-retryable',
        'template': ('URL {url} is not safe to open (non-retryable error)\n'
                     "You can only use the exact same URL from the previous search results or the user's message"),
        'source': 'Backend assistant reports in web-ref-api-probe/2026-09-16-one-click; native results were empty',
    },
    'unsafe_conditions': {
        'label': 'Not safe · full conditions',
        'template': ("URL {url} is not safe to open. You can only directly open a URL if it meets one of the following conditions: "
                     "1. The user provided it or it appears in existing page content. "
                     "2. It's from our own domains. "
                     "3. It's from a third-party domain with a low risk of open redirects. "
                     "4. It's a 'simple' URL without a path, query parameters, or fragments. "
                     "5. It's a simple variant of a safe URL that has been accessed previously. "
                     "6. It's a local file path (e.g. /mnt/data/ or /home/oai/share/). "
                     "7. It's a localhost URL and any url parameters are safe"),
        'source': 'Conditions supplied by the user on 2026-09-17; also present in run 40e34d88bfe7',
    },
}


def error_text(kind, url):
    return PRESETS[kind]['template'].replace('{url}', url)
