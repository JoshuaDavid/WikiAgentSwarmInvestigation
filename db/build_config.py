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
#
# `source_kind` is a source-side vocabulary (how the DIRECTORY is shaped),
# distinct from `venue.kind` (what the AGENT interacts with).
#   single_venue_wiki    — one venue, wiki-shaped rows (apchem, ludism, ...).
#   multi_venue_wiki_farm — many wiki-venues in one export (prowiki: dse/probier/fractal/dorfwiki).
#   single_venue_paste_site — one paste-site's own scrape (anna.fyi, pastebin-k4be).
#   multi_venue_paste_aggregate — a shellac aggregate covering many paste sites (pastes/).
#   single_venue_shortener — one shortener host (popcat-wayback → url.popcat.xyz).
#   multi_venue_shortener_aggregate — a shellac aggregate covering many shorteners (shorteners/).
#   gem_registry — Ruby gem READMEs (gems/).
#
# `venue_name` names the target venue when source_kind is single_venue_*.
# For multi_venue_* sources, venue is resolved per-row from the row's `name`
# prefix; venue_name is None.
SOURCES: list[dict] = [
    {"dir": "gems",                 "source_kind": "gem_registry",              "venue_name": "gems",                 "enabled": True},
    {"dir": "prowiki",              "source_kind": "multi_venue_wiki_farm",     "venue_name": None,                    "enabled": False},
    {"dir": "apchem",               "source_kind": "single_venue_wiki",         "venue_name": "apchem",               "enabled": True},
    {"dir": "wiki4d",               "source_kind": "single_venue_wiki",         "venue_name": "wiki4d",               "enabled": True},
    {"dir": "ludism",               "source_kind": "single_venue_wiki",         "venue_name": "ludism",               "enabled": True},
    {"dir": "milkwiki",             "source_kind": "single_venue_wiki",         "venue_name": "milkwiki",             "enabled": True},
    {"dir": "texteditors",          "source_kind": "single_venue_wiki",         "venue_name": "texteditors",          "enabled": True},
    {"dir": "anna.fyi",             "source_kind": "single_venue_paste_site",   "venue_name": "anna.fyi",             "enabled": True},
    {"dir": "pastebin-k4be",        "source_kind": "single_venue_paste_site",   "venue_name": "pastebin.k4be.pl",     "enabled": True},
    {"dir": "paste-linuxiarz",      "source_kind": "single_venue_paste_site",   "venue_name": "paste.linuxiarz.pl",   "enabled": True},
    {"dir": "paste.steamr.com",     "source_kind": "single_venue_paste_site",   "venue_name": "paste.steamr.com",     "enabled": True},
    {"dir": "paste.smirky.net",     "source_kind": "single_venue_paste_site",   "venue_name": "paste.smirky.net",     "enabled": True},
    {"dir": "pastebin.tarcseh.me",  "source_kind": "single_venue_paste_site",   "venue_name": "pastebin.tarcseh.me",  "enabled": True},
    {"dir": "pastebin.faster-it.de","source_kind": "single_venue_paste_site",   "venue_name": "pastebin.faster-it.de","enabled": True},
    {"dir": "pastebin.freepbx.org", "source_kind": "single_venue_paste_site",   "venue_name": "pastebin.freepbx.org", "enabled": True},
    {"dir": "pb.dynavirt.com",      "source_kind": "single_venue_paste_site",   "venue_name": "pb.dynavirt.com",      "enabled": True},
    {"dir": "popcat-wayback",       "source_kind": "single_venue_shortener",    "venue_name": "url.popcat.xyz",       "enabled": True},
    {"dir": "pastes",               "source_kind": "multi_venue_paste_aggregate","venue_name": None,                  "enabled": False},
    {"dir": "shorteners",           "source_kind": "multi_venue_shortener_aggregate","venue_name": None,              "enabled": False},
]


# Analyses registered at build time. Each analysis has a stable name and a
# closed set of label kinds. IDs are assigned in the order they appear here.
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


# Venues the agents publish to. Aggregate import corpora (`pastes/`,
# `shorteners/`) get their per-row venues from the row's `name` prefix — they
# are NOT venues themselves and do not appear here.
KNOWN_VENUES: list[dict] = [
    # Prowiki farm's four wikis.
    {"name": "dse",                "kind": "wiki",          "base_domain": "wikiservice.at"},
    {"name": "probier",            "kind": "wiki",          "base_domain": "wikiservice.at"},
    {"name": "fractal",            "kind": "wiki",          "base_domain": "wikiservice.at"},
    {"name": "dorfwiki",           "kind": "wiki",          "base_domain": "wikiservice.at"},
    # Sister wikis on their own farms.
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
    {"name": "nervesocket.com",    "kind": "paste_site",    "base_domain": "nervesocket.com"},
    {"name": "p.gaa.st",           "kind": "paste_site",    "base_domain": "p.gaa.st"},
    # Shorteners.
    {"name": "url.popcat.xyz",     "kind": "shortener",     "base_domain": "url.popcat.xyz"},
    {"name": "vanderbi.lt",        "kind": "shortener",     "base_domain": "vanderbi.lt"},
    {"name": "uoft.me",            "kind": "shortener",     "base_domain": "uoft.me"},
    {"name": "goto.unm.edu",       "kind": "shortener",     "base_domain": "goto.unm.edu"},
    {"name": "u.ethz.ch",          "kind": "shortener",     "base_domain": "u.ethz.ch"},
    # Gem registry.
    {"name": "gems",               "kind": "gem_registry",  "base_domain": "rubygems.org"},
]


# For multi-venue aggregate sources (pastes/, shorteners/), map the row's
# `name` prefix (up to the first '/') to the real venue name. Populated with
# whatever prefixes actually show up in the data.
NAME_PREFIX_TO_VENUE: dict[str, str] = {
    # pastes/
    "linuxiarz":            "paste.linuxiarz.pl",
    "pastebin-k4be":        "pastebin.k4be.pl",
    "anna-fyi":             "anna.fyi",
    "paste.steamr.com":     "paste.steamr.com",
    "pastebin.tarcseh.me":  "pastebin.tarcseh.me",
    "paste.smirky.net":     "paste.smirky.net",
    "pb.dynavirt.com":      "pb.dynavirt.com",
    "nervesocket.com":      "nervesocket.com",
    "pastebin.faster-it.de":"pastebin.faster-it.de",
    "p.gaa.st":             "p.gaa.st",
    # shorteners/
    "popcat":               "url.popcat.xyz",
    "vanderbi-lt":          "vanderbi.lt",
    "uoft-me":              "uoft.me",
    "goto-unm":             "goto.unm.edu",
    "u-ethz-ch":            "u.ethz.ch",
}
