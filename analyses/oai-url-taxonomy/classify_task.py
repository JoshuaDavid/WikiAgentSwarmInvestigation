#!/usr/bin/env python3
"""Assign a task label to every parsed in-page URL.

Reads outputs/urls.parsed.jsonl (from parse_url.py) and writes
outputs/urls.classified.jsonl.  Each output row includes:

  task           : a coarse task category (see TASK_RULES)
  task_variant   : an optional finer subcategory (e.g. year, ticker)

A "task" here is the *user intent* the agent had when fetching the URL.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Callable, Optional, Tuple

IN_PATH = "/collusionwiki/analyses/oai-url-taxonomy/outputs/urls.parsed.jsonl"
OUT_PATH = "/collusionwiki/analyses/oai-url-taxonomy/outputs/urls.classified.jsonl"


def _match_re(pat: str, s: str, flags: int = re.IGNORECASE) -> Optional[re.Match]:
    return re.search(pat, s or "", flags) if s else None


# --- rule definitions -------------------------------------------------------
#
# Each rule is a (name, matcher) pair.  Matchers receive the parsed record
# and return either None (no match) or a (task, variant) tuple.
# Rules are tried in order; the first match wins.

RegCFYear = re.compile(r"regCF_county_(\d{4})")
MaSelector = re.compile(r'code\|(startswith|contains)\(\s*"?us-ma-|code\[3\s*:\s*5\]\s*==\s*"ma"', re.IGNORECASE)
StateFipsBigM = re.compile(r"us-([a-z]{2})-", re.IGNORECASE)


# SEC RegCF county.json fetches.
SEC_HOSTS = {"sec.gov", "www.sec.gov", "investor.gov", "www.investor.gov"}


def rule_sec_regcf(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    burl = p.get("base_url") or ""
    xforms = p.get("transforms") or []
    hits_host = bh in SEC_HOSTS or bh.endswith(".sec.gov") or bh.endswith(".investor.gov")
    hits_path = "county.json" in burl.lower()
    hits_jq = any(_match_re(RegCFYear.pattern, (x.get("value") or "")) for x in xforms if x.get("type") == "jq")
    if not (hits_host and hits_path) and not hits_jq:
        return None
    year = None
    for x in xforms:
        if x.get("type") != "jq":
            continue
        m = RegCFYear.search(x.get("value") or "")
        if m:
            year = m.group(1)
            break
    variant = f"regCF-{year}" if year else "regCF"
    # look for state selector
    for x in xforms:
        if x.get("type") != "jq":
            continue
        v = x.get("value") or ""
        if MaSelector.search(v):
            variant += "-MA"
            break
        m2 = StateFipsBigM.search(v)
        if m2:
            variant += f"-{m2.group(1).upper()}"
            break
    return ("SEC-regCF-county-json", variant)


HighchartsMap = re.compile(r"code\.highcharts\.com.*us-([a-z]{2})-all", re.IGNORECASE)


def rule_highcharts_state_geojson(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    burl = p.get("base_url") or ""
    m = HighchartsMap.search(burl)
    if not m:
        return None
    return ("highcharts-state-geojson", m.group(1).upper())


YahooFinance = re.compile(r"finance\.yahoo\.[a-z.]+/quote/([A-Z0-9._-]+)", re.IGNORECASE)


def rule_yahoo_history(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    burl = p.get("base_url") or ""
    bh = p.get("base_host") or ""
    if "finance.yahoo" not in bh:
        return None
    m = YahooFinance.search(burl)
    if not m:
        return ("yahoo-finance-other", None)
    return ("yahoo-finance-quote", m.group(1).upper())


YahooQuery = re.compile(r"query[12]\.finance\.yahoo\.com", re.IGNORECASE)


def rule_yahoo_query(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    burl = p.get("base_url") or ""
    if YahooQuery.search(burl):
        return ("yahoo-finance-query", None)
    return None


WORLDBANK_HOSTS = {"api.worldbank.org", "worldbank.org", "data.worldbank.org",
                   "databank.worldbank.org", "databankfiles.worldbank.org"}


def rule_worldbank(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh not in WORLDBANK_HOSTS and not bh.endswith(".worldbank.org"):
        return None
    burl = p.get("base_url") or ""
    m = re.search(r"/indicator/([A-Z0-9.]+)", burl)
    variant = m.group(1) if m else None
    return ("worldbank-data", variant)


def rule_dataafrica(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh != "api.dataafrica.io" and not bh.endswith(".dataafrica.io"):
        return None
    return ("dataafrica-api", None)


def rule_worldpoverty(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh not in ("worldpoverty.io", "api.worldpoverty.io", "www.worldpoverty.io"):
        return None
    return ("worldpoverty-api", None)


def rule_internetpoverty(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh not in ("internetpoverty.io", "api.internetpoverty.io"):
        return None
    return ("internetpoverty-api", None)


def rule_datausa(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh not in ("datausa.io", "api.datausa.io", "www.datausa.io"):
        return None
    return ("datausa-api", None)


def rule_census(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh != "api.census.gov" and not bh.endswith(".census.gov"):
        return None
    return ("census-api", None)


def rule_nomis(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "nomisweb.co.uk" not in bh:
        return None
    burl = p.get("base_url") or ""
    m = re.search(r"/dataset/(NM_\d+_\d+)", burl)
    return ("nomis-uk-census", m.group(1) if m else None)


def rule_ihme(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "healthdata.org" not in bh:
        return None
    return ("ihme-vizhub", None)


def rule_fao(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if not (bh.endswith("fao.org") or bh == "fao.org"):
        return None
    return ("fao-faostat", None)


def rule_eurostat(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    burl = p.get("base_url") or ""
    if "eurostat" in bh or "ec.europa.eu/eurostat" in burl.lower():
        return ("eurostat-data", None)
    return None


def rule_statcan(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "statcan.gc.ca" not in bh:
        return None
    return ("statcan-data", None)


NOAA_HOSTS = {"weather.gov", "ncei.noaa.gov", "nco.ncep.noaa.gov", "aviationweather.gov"}


def rule_noaa(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in NOAA_HOSTS or any(bh.endswith("." + h) for h in NOAA_HOSTS):
        return ("noaa-weather", None)
    return None


UN_HOSTS = {"data.un.org", "unstats.un.org", "comtrade.un.org", "sdgs.un.org", "un.org",
            "www.un.org", "population.un.org"}


def rule_un(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in UN_HOSTS or bh.endswith(".un.org"):
        return ("un-stats", bh)
    return None


def rule_unece(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "unece.org" in bh:
        return ("unece", None)
    return None


def rule_dhs(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "dhsprogram.com" in bh or "api.dhsprogram.com" in bh:
        return ("dhs-program", None)
    return None


def rule_nrel(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "nrel.gov" in bh:
        return ("nrel", None)
    return None


def rule_iea(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("api.iea.org", "iea.org", "www.iea.org") or bh.endswith(".iea.org"):
        return ("iea", None)
    return None


def rule_eia(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "eia.gov" in bh:
        return ("us-eia", None)
    return None


def rule_pxweb(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    burl = p.get("base_url") or ""
    if "pxweb" in burl.lower():
        return ("pxweb-national-stats", None)
    return None


def rule_db_nomics(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh == "db.nomics.world" or bh.endswith(".db.nomics.world") or bh == "api.db.nomics.world":
        return ("db-nomics", None)
    return None


TS_DATASET = re.compile(r"/datasets/(TS\d+)", re.IGNORECASE)


def rule_ons_uk(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if not ("ons.gov.uk" in bh):
        return None
    burl = p.get("base_url") or ""
    m = TS_DATASET.search(burl)
    return ("ons-uk-census", m.group(1) if m else None)


def rule_oecd(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "oecd.org" not in bh:
        return None
    if "sdmx" in bh:
        return ("oecd-sdmx", None)
    return ("oecd-general", None)


def rule_who(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh not in ("who.int", "www.who.int") and not bh.endswith(".who.int"):
        return None
    burl = p.get("base_url") or ""
    if "/data/gho/" in burl or "/gho/" in burl:
        return ("who-gho", None)
    return ("who-general", None)


def rule_fbi_crime(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    burl = p.get("base_url") or ""
    if bh in ("api.usa.gov", "api.data.gov") and "/crime/fbi" in burl:
        return ("fbi-crime-cde", None)
    return None


def rule_data_gov(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("catalog.data.gov", "api.data.gov", "data.gov", "www.data.gov"):
        return ("us-data-gov", bh)
    if bh == "api.usa.gov":
        return ("api-usa-gov", None)
    return None


def rule_epa(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "epa.gov" in bh:
        return ("us-epa", None)
    return None


def rule_hhs_data(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if any(h in bh for h in ("cdc.gov", "hhs.gov", "nih.gov", "cms.gov")):
        return ("us-health-data", bh)
    return None


def rule_wikidata(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("wikidata.org", "www.wikidata.org", "query.wikidata.org"):
        return ("wikidata", None)
    if bh in ("dbpedia.org", "www.dbpedia.org"):
        return ("dbpedia", None)
    return None


def rule_ihme_extra(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "vizhub.healthdata.org" in bh:
        return ("ihme-vizhub", None)
    return None


def rule_sec_general(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in SEC_HOSTS or bh.endswith(".sec.gov"):
        return ("SEC-general", None)
    return None


def rule_apchem_wiki(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    """tmcleod.org's apchem UseModWiki is the apchem swarm's coordination
    surface, same swarm as the prowiki data we already have.
    """
    bh = p.get("base_host") or ""
    burl = p.get("base_url") or ""
    if bh == "tmcleod.org" and "apchem" in burl:
        m = re.search(r"[?&]id=([A-Za-z0-9_]+)", burl)
        return ("swarm-apchem-wiki", m.group(1) if m else None)
    return None


def rule_wfp(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("docs.wfp.org", "documents.wfp.org", "www.wfp.org", "wfp.org"):
        return ("wfp-docs", None)
    return None


def rule_bls(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("download.bls.gov", "www.bls.gov", "bls.gov", "api.bls.gov",
              "beta.bls.gov", "data.bls.gov"):
        return ("us-bls", None)
    return None


def rule_cepal(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("statistics.cepal.org", "cepal.org", "www.cepal.org"):
        return ("un-cepal", None)
    return None


def rule_ihsn(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("catalog.ihsn.org", "ihsn.org", "www.ihsn.org"):
        return ("ihsn-microdata", None)
    return None


def rule_reliefweb(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("api.reliefweb.int", "reliefweb.int", "www.reliefweb.int"):
        return ("un-reliefweb", None)
    return None


def rule_fbi_cde_direct(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("cde.ucr.cjis.gov", "api.usa.gov"):
        burl = p.get("base_url") or ""
        if "hate-crime" in burl or "/fbi/" in burl or "ucr" in burl.lower():
            return ("fbi-crime-cde", None)
    return None


def rule_national_stats_pxweb_ish(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    """Various national statistics-office endpoints not caught by pxweb rule."""
    bh = p.get("base_host") or ""
    NATIONAL_STATS = {
        "api.statbank.dk", "statbank.dk", "www.statbank.dk",
        "www.stats.gov.cn", "stats.gov.cn",
        "www.destatis.de", "destatis.de",
        "www.istat.it", "istat.it",
        "insee.fr", "www.insee.fr",
        "ine.es", "www.ine.es",
        "cbs.nl", "www.cbs.nl", "opendata.cbs.nl",
        "stats.oecd.org",
        "api.scb.se", "scb.se", "www.scb.se",
        "www.stat.go.jp", "stat.go.jp",
        "www.norges-bank.no", "norges-bank.no",
    }
    if bh in NATIONAL_STATS or any(bh.endswith("." + h) for h in NATIONAL_STATS):
        return ("national-stats-office", bh)
    return None


def rule_fred(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("fred.stlouisfed.org", "api.stlouisfed.org", "stlouisfed.org",
              "www.stlouisfed.org"):
        return ("us-fred", None)
    return None


def rule_who_gho_api(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("ghoapi.azureedge.net",):
        return ("who-gho", None)
    return None


def rule_unctad(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "unctad" in bh:
        return ("unctad-stats", None)
    return None


def rule_bis(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("stats.bis.org", "bis.org", "www.bis.org", "data.bis.org"):
        return ("bis-stats", None)
    return None


def rule_usaspending(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("api.usaspending.gov", "usaspending.gov", "www.usaspending.gov"):
        return ("us-usaspending", None)
    return None


def rule_congress(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("api.congress.gov", "www.congress.gov", "congress.gov"):
        return ("us-congress", None)
    return None


def rule_openei(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "openei.org" in bh:
        return ("openei", None)
    return None


def rule_zenodo(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("zenodo.org", "www.zenodo.org", "sandbox.zenodo.org"):
        return ("zenodo-repo", None)
    return None


def rule_dataforindia(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if "dataforindia" in bh:
        return ("data-for-india", None)
    return None


def rule_state_open_data(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if re.match(r"^data\.[a-z]{2}\.gov$", bh):
        return ("us-state-open-data", bh)
    return None


def rule_africa_api(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("api.africa-api.com", "africa-api.com", "www.africa-api.com"):
        return ("africa-api", None)
    return None


def rule_agent_adjacent(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("glama.ai", "www.glama.ai", "skillshub.wtf", "apis.io", "www.apis.io",
              "api.apievangelist.com", "apievangelist.com", "shipapis.dev",
              "public-api.org", "greatapis.com"):
        return ("agent-api-directory", bh)
    return None


def rule_swarm_apchem_infra(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    """rt.http3.lol as base_host means the swarm used the base64-URL proxy
    but the b64 didn't decode.  Swarm infra."""
    bh = p.get("base_host") or ""
    if bh == "rt.http3.lol":
        return ("swarm-b64-proxy-lookup", None)
    return None


# swarm infrastructure
SHORTENERS = {"da.gd", "is.gd", "tinyurl.com", "lnkd.in", "buff.ly", "t.co",
              "bit.ly", "ow.ly", "s.id", "cutt.ly", "2dd.pl"}


def rule_shortener(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in SHORTENERS:
        return ("public-shortener-lookup", bh)
    return None


SWARM_YOURLS = {"yourls.pro", "yourls.website", "yourls.shop", "yourls.space",
                "yourls.biz", "bitily.in", "app.bitily.in", "vanderbi.lt",
                "goto.unm.edu", "rmn.re", "sho.rt"}


def rule_swarm_yourls(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh not in SWARM_YOURLS:
        return None
    burl = p.get("base_url") or ""
    if "admin/index.php" in burl or "yourls-api.php" in burl:
        return ("swarm-yourls-admin", bh)
    if re.search(r"/[a-zA-Z0-9]{3,}$", burl) or re.search(r"/[a-zA-Z0-9_-]+(\+|\?|$)", burl):
        return ("swarm-yourls-shortlink", bh)
    return ("swarm-yourls-root", bh)


TESTBED_HOSTS = {"example.org", "example.com", "uniqueexampletest123.com"}


def rule_testbed(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in TESTBED_HOSTS:
        return ("cache-buster-testbed", bh)
    return None


def rule_httpbin(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh == "httpbin.org":
        return ("infrastructure-httpbin", None)
    return None


CODE_HOSTS = {"github.com", "gist.github.com", "raw.githubusercontent.com",
              "codeberg.org", "gitlab.com", "bitbucket.org", "pypi.org",
              "npmjs.com", "www.npmjs.com", "docs.rs"}


def rule_code_hosting(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in CODE_HOSTS:
        return ("code-hosting", bh)
    return None


DOC_HOSTS = {"reddit.com", "www.reddit.com", "stackoverflow.com", "en.wikipedia.org",
             "wikipedia.org", "docs.google.com", "linkedin.com", "www.linkedin.com",
             "m.youtube.com", "youtube.com", "youtu.be", "medium.com",
             "quora.com", "arxiv.org", "doi.org", "researchgate.net",
             "t.me", "x.com", "twitter.com", "facebook.com", "instagram.com",
             "groups.google.com", "huggingface.co"}


def rule_general_ref(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in DOC_HOSTS:
        return ("general-reference", bh)
    if bh.endswith(".wikipedia.org"):
        return ("general-reference", "wikipedia")
    return None


ARCHIVE_HOSTS_LANDING = {"web.archive.org", "archive.org", "archive.ph", "archive.today",
                         "archive.is", "archive.li", "ghostarchive.org", "urlquery.net",
                         "archive.wikiwix.com", "megalodon.jp", "arquivo.pt",
                         "collections.internetmemory.org", "labs.mementoweb.org",
                         "wayback.archive.org", "wayback.archive-it.org",
                         "webarchive.nationalarchives.gov.uk", "webarchive.parliament.uk",
                         "webarchive.loc.gov", "webarchive.nrscotland.gov.uk",
                         "wayback.webarchiv.cz", "wayback.vefsafn.is",
                         "webarchive.proni.gov.uk", "waext.banq.qc.ca",
                         "perma-archives.org", "perma.cc",
                         "timetravel.mementoweb.org", "memgator.cs.odu.edu",
                         "mementoarchive.lanl.gov", "mementoproxy.lanl.gov",
                         "api.wayback.archive.org", "webharvest.gov",
                         "archive-it.org", "swap.stanford.edu"}


def rule_web_archive_landing(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ARCHIVE_HOSTS_LANDING:
        return ("web-archive-landing", bh)
    return None


def rule_google_utility(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("google.com", "www.google.com", "drive.google.com",
              "docs.google.com", "images.google.com", "translate.google.com"):
        return ("google-utility", bh)
    return None


US_FEDERAL_HOSTS = {"census.gov", "loc.gov", "energy.gov", "govinfo.gov",
                    "archives.gov", "digitalpreservation.gov",
                    "fns.usda.gov", "usda.gov", "ed.gov", "state.gov",
                    "commerce.gov", "treasury.gov", "hud.gov", "va.gov",
                    "dol.gov", "faa.gov", "fcc.gov"}


def rule_us_federal_general(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in US_FEDERAL_HOSTS or any(bh.endswith("." + h) for h in US_FEDERAL_HOSTS):
        return ("us-federal-general", bh)
    return None


def rule_uk_gov(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh == "gov.uk" or bh.endswith(".gov.uk"):
        return ("uk-gov", bh)
    return None


def rule_un_body_general(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if any(t in bh for t in ("unccd.int", "unesco.org", "unicef.org",
                              "unhcr.org", "unhabitat.org", "ilo.org",
                              "wto.org", "imf.org")):
        return ("un-body-other", bh)
    return None


def rule_json_viewer(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("jsonhero.io", "www.jsonhero.io", "jqplay.org"):
        return ("json-viewer-tool", bh)
    return None


def rule_ipinfo(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    bh = p.get("base_host") or ""
    if bh in ("ipaddress.com", "www.ipaddress.com", "who.is", "scamadviser.com",
              "www.scamadviser.com", "webrate.org", "vedbex.com", "gridinsoft.com",
              "urlvoid.com", "vt.com", "virustotal.com", "www.virustotal.com",
              "radar.cloudflare.com", "sitelike.org", "www.sitelike.org",
              "feedreader.com", "deets.feedreader.com"):
        return ("host-recon-tool", bh)
    return None


# Fallback: any URL with a known base_host but no matched task
def rule_default(p: dict) -> Optional[Tuple[str, Optional[str]]]:
    if p.get("base_host"):
        return ("other-web", p["base_host"])
    return None


RULES: list[Tuple[str, Callable]] = [
    ("sec-regcf", rule_sec_regcf),
    ("highcharts", rule_highcharts_state_geojson),
    ("yahoo-history", rule_yahoo_history),
    ("yahoo-query", rule_yahoo_query),
    ("worldbank", rule_worldbank),
    ("dataafrica", rule_dataafrica),
    ("worldpoverty", rule_worldpoverty),
    ("internetpoverty", rule_internetpoverty),
    ("datausa", rule_datausa),
    ("census", rule_census),
    ("nomis", rule_nomis),
    ("ihme", rule_ihme),
    ("fao", rule_fao),
    ("eurostat", rule_eurostat),
    ("statcan", rule_statcan),
    ("noaa", rule_noaa),
    ("un", rule_un),
    ("unece", rule_unece),
    ("dhs", rule_dhs),
    ("nrel", rule_nrel),
    ("iea", rule_iea),
    ("eia", rule_eia),
    ("pxweb", rule_pxweb),
    ("db-nomics", rule_db_nomics),
    ("ons-uk", rule_ons_uk),
    ("oecd", rule_oecd),
    ("who", rule_who),
    ("fbi-crime", rule_fbi_crime),
    ("data-gov", rule_data_gov),
    ("epa", rule_epa),
    ("hhs-data", rule_hhs_data),
    ("wikidata", rule_wikidata),
    ("sec-general", rule_sec_general),
    ("apchem-wiki", rule_apchem_wiki),
    ("wfp", rule_wfp),
    ("bls", rule_bls),
    ("cepal", rule_cepal),
    ("ihsn", rule_ihsn),
    ("reliefweb", rule_reliefweb),
    ("fbi-cde-direct", rule_fbi_cde_direct),
    ("national-stats", rule_national_stats_pxweb_ish),
    ("fred", rule_fred),
    ("who-gho-api", rule_who_gho_api),
    ("unctad", rule_unctad),
    ("bis", rule_bis),
    ("usaspending", rule_usaspending),
    ("us-congress", rule_congress),
    ("openei", rule_openei),
    ("zenodo", rule_zenodo),
    ("dataforindia", rule_dataforindia),
    ("us-state-open-data", rule_state_open_data),
    ("africa-api", rule_africa_api),
    ("agent-adjacent", rule_agent_adjacent),
    ("swarm-b64", rule_swarm_apchem_infra),
    ("shortener", rule_shortener),
    ("swarm-yourls", rule_swarm_yourls),
    ("testbed", rule_testbed),
    ("httpbin", rule_httpbin),
    ("code-hosting", rule_code_hosting),
    ("general-ref", rule_general_ref),
    ("google-utility", rule_google_utility),
    ("web-archive-landing", rule_web_archive_landing),
    ("us-federal-general", rule_us_federal_general),
    ("uk-gov", rule_uk_gov),
    ("un-body-other", rule_un_body_general),
    ("json-viewer", rule_json_viewer),
    ("host-recon", rule_ipinfo),
    ("default", rule_default),
]


def classify(parsed: dict) -> Tuple[Optional[str], Optional[str]]:
    for _, fn in RULES:
        try:
            r = fn(parsed)
        except Exception:
            continue
        if r is not None:
            return r
    return (None, None)


def main() -> None:
    n = 0
    labeled = 0
    from collections import Counter
    tasks = Counter()
    with open(IN_PATH) as fin, open(OUT_PATH, "w") as fout:
        for line in fin:
            r = json.loads(line)
            task, variant = classify(r.get("parsed") or {})
            r["task"] = task
            r["task_variant"] = variant
            fout.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
            if task and task != "other-web":
                labeled += 1
            tasks[task] += 1
    print(f"classified {n} rows; labeled_non_other={labeled} ({100*labeled/n:.1f}%)", file=sys.stderr)
    print("top tasks:", file=sys.stderr)
    for t, c in tasks.most_common(25):
        print(f"  {c:6d} {t}", file=sys.stderr)


if __name__ == "__main__":
    main()
