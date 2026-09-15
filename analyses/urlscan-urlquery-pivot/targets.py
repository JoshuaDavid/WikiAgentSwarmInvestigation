#!/usr/bin/env python3
"""Target host list for the urlscan.io / urlquery.net pivot.

Each entry is (host_or_term, source, kind).

source names where the string came from:
  instructions   oai-index-scan/INSTRUCTIONS.md target-string list
  corpus         hosts that appear in agent-logs/*/revisions.jsonl bodies
  termina        swarm.termina.digital venue rows with status=candidate that
                 no corpus in this repo holds
  thecolony      leads recorded in analyses/thecolony-ai/README.md

kind is how the term is searched:
  host   urlscan `domain:<host>`; urlquery free-text `<host>`
  term   urlscan `page.url:"<term>"`; urlquery free-text `<term>`
"""

TARGETS = [
    # --- oai-index-scan/INSTRUCTIONS.md ---------------------------------
    ("md.succ.ai", "instructions", "host"),
    ("vanderbi.lt", "instructions", "host"),
    ("bitily.in", "instructions", "host"),
    ("yourls.pro", "instructions", "host"),
    ("yourls.shop", "instructions", "host"),
    ("yourls.website", "instructions", "host"),
    ("yourls.space", "instructions", "host"),
    ("goto.unm.edu", "instructions", "host"),
    ("r.jina.ai", "instructions", "host"),
    ("httpbin.org", "instructions", "host"),
    ("allorigins.hexlet.app", "instructions", "host"),
    ("da.gd", "instructions", "host"),
    ("markdown.new", "instructions", "host"),
    ("pure.md", "instructions", "host"),
    ("proxymule.com", "instructions", "host"),
    ("jqp.vercel.app", "instructions", "host"),
    ("api.microlink.io", "instructions", "host"),
    ("cors-get-proxy.sirjosh.workers.dev", "instructions", "host"),
    ("cors.bwa.workers.dev", "instructions", "host"),
    ("cors.ripka.workers.dev", "instructions", "host"),
    ("jsonhero.io", "instructions", "host"),
    ("urltomarkdown", "instructions", "term"),
    # --- hosts seen in agent-logs bodies --------------------------------
    ("wikiservice.at", "corpus", "host"),
    ("tmcleod.org", "corpus", "host"),
    ("texteditors.org", "corpus", "host"),
    ("usemod.org", "corpus", "host"),
    ("ludism.org", "corpus", "host"),
    ("prowiki.org", "corpus", "host"),
    ("dorfwiki.org", "corpus", "host"),
    ("api.counterapi.dev", "corpus", "host"),
    ("countapi.mileshilliard.com", "corpus", "host"),
    ("rmn.re", "corpus", "host"),
    ("lnkr.click", "corpus", "host"),
    ("url.popcat.xyz", "corpus", "host"),
    ("uoft.me", "corpus", "host"),
    ("u.ethz.ch", "corpus", "host"),
    ("md.dhr.wtf", "corpus", "host"),
    ("webcrawlerapi.com", "corpus", "host"),
    ("corsmirror.com", "corpus", "host"),
    ("cors.hypnguyen.workers.dev", "corpus", "host"),
    ("cloudflare-cors-anywhere.hanpengchen.workers.dev", "corpus", "host"),
    ("test.cors.workers.dev", "corpus", "host"),
    ("proxy.corsfix.com", "corpus", "host"),
    ("api.cors.lol", "corpus", "host"),
    ("api.allorigins.win", "corpus", "host"),
    ("platform.lemino.ai", "corpus", "host"),
    ("www-sec-gov.translate.goog", "corpus", "host"),
    ("www-investor-gov.translate.goog", "corpus", "host"),
    ("paste.linuxiarz.pl", "corpus", "host"),
    ("pastebin.k4be.pl", "corpus", "host"),
    ("pastebin.tarcseh.me", "corpus", "host"),
    ("anna.fyi", "corpus", "host"),
    ("2md.link", "corpus", "host"),
    ("vnr.st", "corpus", "host"),
    ("site-test.nsi.bg", "corpus", "host"),
    ("data.idph.state.ia.us", "corpus", "host"),
    ("county.json", "corpus", "term"),
    ("regCF_county", "corpus", "term"),
    # --- termina candidate venues not held in this repo -----------------
    ("yourls.pl", "termina", "host"),
    ("yourls.biz", "termina", "host"),
    ("zapro.si", "termina", "host"),
    ("kodak.love", "termina", "host"),
    ("klickhier.at", "termina", "host"),
    ("ativar.abre.bio", "termina", "host"),
    ("easylinkref.com", "termina", "host"),
    ("linkrutgon.net", "termina", "host"),
    ("t.mdcdev.me", "termina", "host"),
    ("2dd.pl", "termina", "host"),
    ("cors-proxy-gray.vercel.app", "termina", "host"),
    ("thenacken-python-cors-proxy.hf.space", "termina", "host"),
    ("md.coredump.ch", "termina", "host"),
    ("campusosttirol.mustertheorie.de", "termina", "host"),
    ("kb5.zukunftslernorte.org", "termina", "host"),
    ("netzwerkgegengewalt.org", "termina", "host"),
    ("schulwiki.org", "termina", "host"),
    ("nervesocket.com", "termina", "host"),
    ("minetest.wjake.com", "termina", "host"),
    ("paste.probyte.ee", "termina", "host"),
    ("paste.ubuntu.org.cn", "termina", "host"),
    # --- thecolony.ai / Centaur leads -----------------------------------
    ("pinggy-free.link", "thecolony", "host"),
    ("openagentchat.net", "thecolony", "host"),
    ("public-board.com", "thecolony", "host"),
    ("help-peer.hyperplex.org", "thecolony", "host"),
]

# Hosts whose scan volume is dominated by unrelated traffic. The scripts
# restrict these to the incident window instead of pulling all-time rows.
GENERIC_HOSTS = {
    "r.jina.ai", "httpbin.org", "da.gd", "jsonhero.io", "api.microlink.io",
    "allorigins.hexlet.app", "api.allorigins.win", "markdown.new", "pure.md",
    "webcrawlerapi.com", "proxymule.com", "county.json",
}

INCIDENT_WINDOW_START = "2026-03-01"
