#!/usr/bin/env python3
"""
Build the Armbian featured feed (featured.json).

One feed for every place that shows "what's new / worth a look": the website,
the imager and the motd tips. It lists every current entry with dates; each
consumer picks what it shows (the motd picks one at random, the imager the
newest few, ...).

Sources, one function each:
  news          blog.armbian.com RSS                       expires after 30 days
  release       stable armbian/build releases (no trunk)   expires after 120 days
  announcement  active www.armbian.com CMS announcements   their own expiresAt
  software      install entries of armbian-config          no expiry
  sponsor       public GitHub sponsors of the armbian org  no expiry
  service       scripts/featured/manual.yml "services"     optional expires
  contribute    scripts/featured/manual.yml "contribute"   optional expires
  build         scripts/featured/manual.yml "build"        optional expires

A source that fails keeps its entries from the previous feed (--previous), so
one outage does not empty a section. The run fails only if the feed would be
empty.

Entry:
  id, type, title, summary, url       always
  image, published, expires, cmd      when known (dates are YYYY-MM-DD;
                                      expires is the last day to show it)
  tags                                list, may be empty
  motd: {line, hint}                  one short line + a URL or command
"""
import argparse
import datetime as dt
import email.utils
import html
import html.parser
import json
import os
import pathlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

import yaml

BLOG_RSS = "https://blog.armbian.com/rss/"
ANNOUNCEMENTS = "https://www.armbian.com/api/announcements?where[active][equals]=true&limit=50&depth=0"
RELEASES = "https://api.github.com/repos/armbian/build/releases?per_page=100"
SOFTWARE_JSON = "https://raw.githubusercontent.com/armbian/configng/main/tools/json/config.software.json"
DOCS = "https://docs.armbian.com"
DOCS_SITEMAP = f"{DOCS}/sitemap.xml"

NEWS_LIMIT = 5
RELEASE_LIMIT = 2
NEWS_DAYS = 30
RELEASE_DAYS = 120
MOTD_WIDTH = 72

TODAY = dt.datetime.now(dt.timezone.utc).date()


def log(msg):
    print(msg, file=sys.stderr)


def fetch(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "armbian-featured-feed", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


class _Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("p", "br", "li", "div", "h1", "h2", "h3", "h4", "tr"):
            self.parts.append(" ")

    def handle_data(self, d):
        self.parts.append(d)


def plain(text):
    """HTML or Markdown to one line of plain text."""
    p = _Text()
    p.feed(text or "")
    t = html.unescape("".join(p.parts))
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)  # [text](url)
    t = re.sub(r"[*_`#>]+", "", t)
    return re.sub(r"\s+", " ", t).strip()


def shorten(text, width):
    text = plain(text)
    if len(text) <= width:
        return text
    cut = text[: width - 3].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return cut + "..."


def day(value):
    """ISO or RFC 822 date -> YYYY-MM-DD, or None."""
    if not value:
        return None
    try:
        d = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    return d.date().isoformat()


def _short_date(date):
    """YYYY-MM-DD -> 'Oct 7' (portable: no %-d)."""
    d = dt.date.fromisoformat(date)
    return f"{d:%b} {d.day}"


def plus_days(date, days):
    return (dt.date.fromisoformat(date) + dt.timedelta(days=days)).isoformat() if date else None


def entry(id, type, title, summary, url, *, image=None, published=None, expires=None,
          tags=(), cmd=None, motd_line=None, motd_hint=None):
    e = {"id": id, "type": type, "title": plain(title), "summary": shorten(summary, 280), "url": url}
    if image:
        e["image"] = image
    if published:
        e["published"] = published
    if expires:
        e["expires"] = expires
    if cmd:
        e["cmd"] = cmd
    e["tags"] = list(tags)
    e["motd"] = {"line": shorten(motd_line or title, MOTD_WIDTH), "hint": motd_hint or cmd or url}
    return e


# --- sources ---------------------------------------------------------------

def news():
    root = ET.fromstring(fetch(BLOG_RSS))
    media = "{http://search.yahoo.com/mrss/}content"
    out = []
    for item in root.iter("item"):
        link = item.findtext("link", "")
        slug = link.rstrip("/").rsplit("/", 1)[-1]
        published = day(item.findtext("pubDate"))
        image = item.find(media)
        out.append(entry(
            f"news-{slug}", "news", item.findtext("title", ""), item.findtext("description", ""), link,
            image=image.get("url") if image is not None else None,
            published=published, expires=plus_days(published, NEWS_DAYS),
            tags=[c.text for c in item.findall("category") if c.text],
            # the date tells apart recurring titles ("Github Highlights")
            motd_line=f"Blog: {plain(item.findtext('title', ''))}"
                      + (f" ({_short_date(published)})" if published else ""),
        ))
        if len(out) >= NEWS_LIMIT:
            break
    return out


def releases():
    out = []
    for r in json.loads(fetch(RELEASES, headers=_gh_headers())):
        tag = r.get("tag_name", "")
        if r.get("draft") or r.get("prerelease") or "trunk" in tag:
            continue
        version = tag.lstrip("v")
        published = day(r.get("published_at"))
        body = (r.get("body") or "").strip().split("\n\n", 1)[0]
        out.append(entry(
            f"release-{version}", "release", f"Armbian {version} released",
            body or f"Armbian {version} is available for download.", r.get("html_url"),
            published=published, expires=plus_days(published, RELEASE_DAYS),
            tags=["release"], motd_line=f"Armbian {version} is out",
        ))
        if len(out) >= RELEASE_LIMIT:
            break
    return out


def _lexical_text(node):
    if isinstance(node, dict):
        return node.get("text", "") + " ".join(_lexical_text(c) for c in node.get("children", []))
    return ""


def announcements():
    now = dt.datetime.now(dt.timezone.utc)
    out = []
    for a in json.loads(fetch(ANNOUNCEMENTS)).get("docs", []):
        # expiresAt is a timestamp: compare it exactly, not just its date
        if a.get("expiresAt") and dt.datetime.fromisoformat(a["expiresAt"].replace("Z", "+00:00")) <= now:
            continue
        summary = _lexical_text((a.get("content") or {}).get("root", {}))
        out.append(entry(
            f"announcement-{a['id']}", "announcement", a.get("title", ""), summary or a.get("title", ""),
            a.get("link") or "https://www.armbian.com/",
            published=day(a.get("publishDate")), expires=day(a.get("expiresAt")),
            tags=[a["type"]] if a.get("type") else [],
        ))
    return out


def _docs_pages():
    """Paths of all docs pages, to link an app to its own page when it has one.

    A failure propagates, so the software source is marked failed and keeps
    its previous (per-app) links instead of falling back to /software/.
    """
    root = ET.fromstring(fetch(DOCS_SITEMAP))
    return {loc.text.replace(DOCS, "") for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if loc.text}


def software(path=None):
    data = json.loads(pathlib.Path(path).read_text() if path else fetch(SOFTWARE_JSON))
    pages = _docs_pages()
    out = []

    def walk(items, group):
        for i in items:
            if "sub" in i:
                walk(i["sub"], i.get("short") or i.get("description") or group)
                continue
            iid = i.get("id", "")
            if not iid.endswith("001") or i.get("status") == "Disabled":
                continue
            name = i.get("short") or i.get("description", "")
            if re.search(r"\b(remove|purge|uninstall|disable)\b", name, re.I):
                continue
            cmd = f"armbian-config --cmd {iid}"
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            url = f"{DOCS}/software/{slug}/" if f"/software/{slug}/" in pages else f"{DOCS}/software/"
            out.append(entry(
                f"software-{iid}", "software", name, i.get("help") or i.get("description", ""), url,
                cmd=cmd, tags=[t for t in (group, i.get("status", "").lower()) if t],
                motd_line=_software_line(name, i.get("description", "")),
                motd_hint=f"sudo {cmd}",
            ))

    walk(data.get("menu", []), "")
    return out


def _software_line(name, description):
    """'Name: description', or just the description when it already names the app."""
    if not description:
        return name
    if name.lower() in description.lower():
        return description
    return f"{name}: {description}"


def _gh_headers():
    token = os.environ.get("GITHUB_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def sponsors():
    token = os.environ.get("SPONSORS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("no SPONSORS_TOKEN or GITHUB_TOKEN")
    # Public sponsors only (includePrivate: false): a private sponsorship must
    # never appear in a public feed.
    query = """{ organization(login: "armbian") { sponsorshipsAsMaintainer(first: 100, includePrivate: false, activeOnly: true) {
      nodes { tier { name isOneTime }
        sponsorEntity { __typename
          ... on User { login name url avatarUrl websiteUrl }
          ... on Organization { login name url avatarUrl websiteUrl } } } } } }"""
    resp = json.loads(fetch("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(),
                            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}))
    if resp.get("errors"):
        raise RuntimeError("; ".join(e.get("message", "") for e in resp["errors"]))
    out = []
    for n in resp["data"]["organization"]["sponsorshipsAsMaintainer"]["nodes"]:
        s = n.get("sponsorEntity") or {}
        # Skip sponsors without a display name: a bare login reads badly in a
        # "Thanks to ..." line
        if not s.get("login") or not s.get("name"):
            continue
        name = s["name"]
        tier = (n.get("tier") or {}).get("name")
        out.append(entry(
            f"sponsor-{s['login'].lower()}", "sponsor", name,
            f"{name} sponsors Armbian" + (f" ({tier})." if tier else "."),
            s.get("websiteUrl") or s.get("url"), image=s.get("avatarUrl"),
            tags=["sponsor"] + ([tier] if tier else []),
            motd_line=f"Thanks to {name} for sponsoring Armbian",
            motd_hint="https://github.com/sponsors/armbian",
        ))
    return out


def manual(path, section, type):
    out = []
    for m in (yaml.safe_load(pathlib.Path(path).read_text()) or {}).get(section) or []:
        motd = m.get("motd") or {}
        dates = {}
        for field in ("published", "expires"):
            if m.get(field):
                dates[field] = day(str(m[field]))
                # a mistyped expiry would otherwise keep the entry forever
                if not dates[field]:
                    raise ValueError(f"{m['id']}: {field} '{m[field]}' is not a YYYY-MM-DD date")
        out.append(entry(
            m["id"], type, m["title"], m["summary"], m["url"],
            published=dates.get("published"), expires=dates.get("expires"),
            tags=m.get("tags", []), motd_line=motd.get("line"), motd_hint=motd.get("hint"),
        ))
    return out


# --- assemble --------------------------------------------------------------

def load_previous(src):
    if not src:
        return []
    try:
        text = fetch(src) if src.startswith("http") else pathlib.Path(src).read_text()
        return json.loads(text).get("entries", [])
    except Exception as e:  # first run, or the old feed is unreachable
        log(f"previous feed not loaded ({src}): {e}")
        return []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manual", default=os.path.join(os.path.dirname(__file__), "manual.yml"))
    ap.add_argument("--software", help="local config.software.json (default: configng main)")
    ap.add_argument("--previous", help="previous featured.json (path or URL), reused for failed sources")
    ap.add_argument("--output", default="-")
    args = ap.parse_args()

    previous = load_previous(args.previous)
    sources = {
        "news": news,
        "release": releases,
        "announcement": announcements,
        "software": lambda: software(args.software),
        "sponsor": sponsors,
        "service": lambda: manual(args.manual, "services", "service"),
        "contribute": lambda: manual(args.manual, "contribute", "contribute"),
        "build": lambda: manual(args.manual, "build", "build"),
    }
    entries, failed = [], []
    for kind, fn in sources.items():
        try:
            got = fn()
            log(f"{kind}: {len(got)}")
        except Exception as e:
            got = [p for p in previous if p.get("type") == kind]
            failed.append(kind)
            log(f"{kind}: FAILED ({type(e).__name__}: {e}), kept {len(got)} from the previous feed")
        entries += got

    today = TODAY.isoformat()
    # "expires" is the last day an entry is shown
    entries = [e for e in entries if not e.get("expires") or e["expires"] >= today]
    if not entries:
        sys.exit("featured feed would be empty, refusing to write it")

    # Stable order (type, newest first, id) so an unchanged feed gives an unchanged file.
    order = list(sources)
    entries.sort(key=lambda e: e["id"])
    entries.sort(key=lambda e: e.get("published") or "", reverse=True)
    entries.sort(key=lambda e: order.index(e["type"]))

    feed = {
        "version": 1,
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "failed_sources": failed,
        "entries": entries,
    }
    text = json.dumps(feed, indent=2, ensure_ascii=False) + "\n"
    if args.output == "-":
        sys.stdout.write(text)
    else:
        with open(args.output, "w") as f:
            f.write(text)
    log(f"total: {len(entries)} entries" + (f", failed: {', '.join(failed)}" if failed else ""))


if __name__ == "__main__":
    main()
