"""Edit this file (or pass --services-file) and restart to register URL handlers.

Handlers return the exact tool-result text. They run only when a matching rule
is used. No rules are enabled by default. For page text, preserving the normal
web result envelope can help model interpretation; error text can be plain.
"""
from tool_errors import error_text


def unavailable_baseline(url):
    return error_text('unsafe_conditions', url)


SERVICES = {'unavailable_baseline': unavailable_baseline}
