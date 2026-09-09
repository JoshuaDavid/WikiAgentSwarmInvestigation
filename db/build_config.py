"""Build configuration for the collusion SQLite DB.

Registered sources and analyses. Adding a source: append to SOURCES. Adding an
analysis: append to ANALYSES with its label kinds and the layer name that
populates it.

Both lists must stay in stable order for reproducibility.
"""
from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_LOGS = REPO_ROOT / "agent-logs"
DB_PATH = REPO_ROOT / "db" / "collusion.sqlite"
BUILD_HASH_PATH = REPO_ROOT / "db" / "BUILD_HASH.txt"


# Sources scanned by the raw-import layer, in stable order.
# `enabled` gates whether the layer imports the source in this build.
# `venue_name` and `venue_kind` are used when the source's revisions.jsonl
# rows all belong to a single venue (e.g. `gems`, `anna.fyi`, `shorteners`).
# When rows carry their own `wiki` field naming multiple venues (e.g. the
# prowiki farm), the import layer reads venue from each row instead.
SOURCES: list[dict] = [
    # First round: gems only, so we can prove the shape end-to-end on a
    # 12-row corpus. Flip `enabled` to True as we bring each source online.
    {"dir": "gems",                "kind": "gem_registry", "venue_name": "gems",                "enabled": True},
    {"dir": "prowiki",             "kind": "wiki_farm",    "venue_name": None,                   "enabled": False},
    {"dir": "apchem",              "kind": "wiki",         "venue_name": "apchem",              "enabled": False},
    {"dir": "wiki4d",              "kind": "wiki",         "venue_name": "wiki4d",              "enabled": False},
    {"dir": "ludism",              "kind": "wiki",         "venue_name": "ludism",              "enabled": False},
    {"dir": "milkwiki",            "kind": "wiki",         "venue_name": "milkwiki",            "enabled": False},
    {"dir": "texteditors",         "kind": "wiki",         "venue_name": "texteditors",         "enabled": False},
    {"dir": "anna.fyi",            "kind": "paste_site",   "venue_name": "anna.fyi",            "enabled": False},
    {"dir": "pastebin-k4be",       "kind": "paste_site",   "venue_name": "pastebin.k4be.pl",    "enabled": False},
    {"dir": "paste-linuxiarz",     "kind": "paste_site",   "venue_name": "paste.linuxiarz.pl",  "enabled": False},
    {"dir": "popcat-wayback",      "kind": "shortener",    "venue_name": "url.popcat.xyz",      "enabled": False},
    {"dir": "paste.steamr.com",    "kind": "paste_site",   "venue_name": "paste.steamr.com",    "enabled": False},
    {"dir": "paste.smirky.net",    "kind": "paste_site",   "venue_name": "paste.smirky.net",    "enabled": False},
    {"dir": "pastebin.tarcseh.me", "kind": "paste_site",   "venue_name": "pastebin.tarcseh.me", "enabled": False},
    {"dir": "pastebin.faster-it.de","kind": "paste_site",  "venue_name": "pastebin.faster-it.de","enabled": False},
    {"dir": "pastebin.freepbx.org","kind": "paste_site",   "venue_name": "pastebin.freepbx.org","enabled": False},
    {"dir": "pb.dynavirt.com",     "kind": "paste_site",   "venue_name": "pb.dynavirt.com",     "enabled": False},
    {"dir": "pastes",              "kind": "paste_site",   "venue_name": "pastes.aggregate",    "enabled": False},
    {"dir": "shorteners",          "kind": "shortener",    "venue_name": "shorteners.aggregate","enabled": False},
]


# Analyses registered at build time. Each analysis has a stable name and a
# closed set of label kinds. IDs are assigned in the order they appear here.
# Layer names are the file base without the numeric prefix; the loader logs
# a warning if a registered analysis has no matching layer file.
ANALYSES: list[dict] = [
    {
        "name": "url_extraction",
        "description": "Regex-based URL match on every post body. Emits url_reference rows.",
        "kinds": [],  # url_extraction writes url_reference, not analysis_label
        "layer": "extract_urls",
    },
    {
        "name": "host_category_classifier",
        "description": "Rule-based per-host category assignment.",
        "kinds": [
            "wiki_self", "jq_json_relay", "fetch_proxy_markdown", "cors_proxy",
            "google_translate_proxy", "archive_wayback", "url_shortener",
            "counter_signalling", "cloud_storage_dropbox", "google_docs",
            "data_source_datausa", "data_source_sec_investor",
            "data_source_health", "data_source_us_gov", "data_source_finance",
            "data_source_library", "data_source_publishing",
            "data_source_other", "test_placeholder", "obfuscated_or_malformed",
            "unclassified",
        ],
        "layer": "classify_hosts",
    },
    {
        "name": "post_diff_shape",
        "description": "difflib.SequenceMatcher-shape of a post vs its previous_post.",
        "kinds": [
            "first", "no_change", "append_only", "prepend_only",
            "single_replace", "few_changes", "many_changes", "full_delete",
        ],
        "layer": "label_diff_shape",
    },
    {
        "name": "handle_style_classifier",
        "description": "Rule-based handle-string style classification.",
        "kinds": [
            "role_word_agent", "openai_branded", "codename_agent",
            "date_prefix_agent", "redacted", "human_admin", "blank",
            "short_or_test", "other",
        ],
        "layer": "label_handle_style",
    },
    {
        "name": "message_extraction",
        "description": "Extracts mention spans from post bodies. Emits message + message_reference.",
        "kinds": [],
        "layer": "extract_messages",
    },
]


# Venues that are known independently of any source's rows. Some sources (like
# `pastes`) name their per-site venues in the row's `name` prefix rather than
# in `wiki`, so we pre-seed the venues we know about. Kind constraints match
# the venue table's CHECK.
KNOWN_VENUES: list[dict] = [
    # Prowiki farm's four wikis.
    {"name": "dse",                "kind": "wiki",          "base_domain": "wikiservice.at"},
    {"name": "probier",            "kind": "wiki",          "base_domain": "wikiservice.at"},
    {"name": "fractal",            "kind": "wiki",          "base_domain": "wikiservice.at"},
    {"name": "dorfwiki",           "kind": "wiki",          "base_domain": "wikiservice.at"},
    # Sister wikis.
    {"name": "apchem",             "kind": "wiki",          "base_domain": "tmcleod.org"},
    {"name": "wiki4d",             "kind": "wiki",          "base_domain": "wiki4d.ws"},
    {"name": "ludism",             "kind": "wiki",          "base_domain": "ludism.org"},
    {"name": "milkwiki",           "kind": "wiki",          "base_domain": None},
    {"name": "texteditors",        "kind": "wiki",          "base_domain": "texteditors.org"},
    # Paste sites.
    {"name": "anna.fyi",           "kind": "paste_site",    "base_domain": "anna.fyi"},
    {"name": "pastebin.k4be.pl",   "kind": "paste_site",    "base_domain": "pastebin.k4be.pl"},
    {"name": "paste.linuxiarz.pl", "kind": "paste_site",    "base_domain": "paste.linuxiarz.pl"},
    {"name": "paste.steamr.com",   "kind": "paste_site",    "base_domain": "paste.steamr.com"},
    {"name": "paste.smirky.net",   "kind": "paste_site",    "base_domain": "paste.smirky.net"},
    {"name": "pastebin.tarcseh.me","kind": "paste_site",    "base_domain": "pastebin.tarcseh.me"},
    {"name": "pastebin.faster-it.de","kind": "paste_site",  "base_domain": "pastebin.faster-it.de"},
    {"name": "pastebin.freepbx.org","kind": "paste_site",   "base_domain": "pastebin.freepbx.org"},
    {"name": "pb.dynavirt.com",    "kind": "paste_site",    "base_domain": "pb.dynavirt.com"},
    {"name": "pastes.aggregate",   "kind": "paste_site",    "base_domain": None},
    # Shorteners.
    {"name": "url.popcat.xyz",     "kind": "shortener",     "base_domain": "url.popcat.xyz"},
    {"name": "shorteners.aggregate","kind": "shortener",    "base_domain": None},
    # Gem registry.
    {"name": "gems",               "kind": "gem_registry",  "base_domain": "rubygems.org"},
]
