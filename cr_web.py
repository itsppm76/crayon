"""Web search, page reading and sandboxed code execution (all free)."""
import html as htmlmod
import ipaddress
import re
import socket
from urllib.parse import urlparse, unquote, parse_qs

import httpx

import cr_config as C
import cr_llm as llm

BROWSER_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
UA = {"User-Agent": "CrayonBot/2.0 (personal assistant bot; https://github.com/itsppm76/crayon)"}
_c = httpx.Client(timeout=httpx.Timeout(15.0, connect=8.0), follow_redirects=False, headers=UA)


def _strip(s):
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def _ddg(query, n=5):
    r = _c.get("https://html.duckduckgo.com/html/", params={"q": query}, headers=BROWSER_UA, timeout=5.0)
    if r.status_code != 200:
        raise RuntimeError(f"search provider HTTP {r.status_code}")
    out = []
    for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]*class="result__a"|$)', r.text, re.S):
        href, title, rest = m.groups()
        if "uddg=" in href:
            href = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
        elif href.startswith("//"):
            href = "https:" + href
        sm = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', rest, re.S)
        if href.startswith("http") and "duckduckgo.com/y.js" not in href:
            out.append({"title": _strip(title)[:150], "url": href, "snippet": _strip(sm.group(1))[:300] if sm else ""})
        if len(out) >= n:
            break
    return out


def _safe_host(host):
    try:
        for fam, _, _, _, sa in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(sa[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except Exception:
        return False


def fetch(url, max_chars=6000):
    for _ in range(4):
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname or not _safe_host(u.hostname):
            raise ValueError("that address isn't allowed")
        r = _c.get(url)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
            url = str(httpx.URL(url).join(r.headers["location"]))
            continue
        break
    else:
        raise RuntimeError("too many redirects")
    if r.status_code != 200:
        raise RuntimeError(f"page returned HTTP {r.status_code}")
    ct = r.headers.get("content-type", "")
    if "html" not in ct and "text" not in ct and "json" not in ct:
        raise RuntimeError(f"unsupported content type {ct[:40]}")
    t = r.text[:600000]
    t = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)[^>]*>.*?</\1>", " ", t)
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", t)
    t = _strip(re.sub(r"(?s)<[^>]+>", " ", t))
    t = re.sub(r"\s+", " ", t)
    return {"title": _strip(title.group(1))[:150] if title else "", "text": t[:max_chars], "truncated": len(t) > max_chars}


def run_code(task):
    """Ask Gemini to solve `task` by writing and running Python in Google's sandbox."""
    out = llm.generate([llm.user(task[:3000])], system="Solve the task by writing and running Python. Reply with the final result only.",
                       tools=[{"code_execution": {}}], temperature=0.0, max_tokens=2000, models=[C.GEMINI_MODEL])
    code, result = "", ""
    for p in out["parts"]:
        if "executableCode" in p:
            code = p["executableCode"].get("code", "")
        if "codeExecutionResult" in p:
            result = p["codeExecutionResult"].get("output", "")
    return {"answer": out["text"][:2000], "code": code[:1500], "output": result[:1500]}


def _mojeek(query, n=5):
    r = _c.get("https://www.mojeek.com/search", params={"q": query}, headers=BROWSER_UA, timeout=5.0)
    if r.status_code != 200:
        raise RuntimeError(f"mojeek HTTP {r.status_code}")
    out = []
    for m in re.finditer(r'<a[^>]*class="title"[^>]*href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]*class="title"|$)', r.text, re.S):
        href, title, rest = m.groups()
        sm = re.search(r'<p class="s"[^>]*>(.*?)</p>', rest, re.S)
        if href.startswith("http"):
            out.append({"title": _strip(title)[:150], "url": href, "snippet": _strip(sm.group(1))[:300] if sm else ""})
        if len(out) >= n:
            break
    return out


def _wiki(query, n=5):
    r = _c.get("https://en.wikipedia.org/w/api.php", params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": n})
    if r.status_code != 200:
        raise RuntimeError(f"wikipedia HTTP {r.status_code}")
    return [{"title": x["title"], "url": "https://en.wikipedia.org/wiki/" + x["title"].replace(" ", "_"), "snippet": _strip(x.get("snippet", ""))} for x in r.json()["query"]["search"]]


def _tavily(query, n=5):
    key = C.env("TAVILY_API_KEY", "")
    if not key:
        raise RuntimeError("no TAVILY_API_KEY")
    news = bool(re.search(r"\b(news|latest|today|yesterday|breaking|score|scores|price|results?|live|this week)\b", query, re.I))
    body = {"query": query[:400], "max_results": n, "topic": "news" if news else "general", "search_depth": "basic"}
    r = _c.post("https://api.tavily.com/search", json=body, headers={"Authorization": "Bearer " + key}, timeout=15.0)
    if r.status_code != 200:
        raise RuntimeError(f"tavily HTTP {r.status_code}")
    return [{"title": x.get("title", "")[:150], "url": x.get("url", ""), "snippet": (x.get("content") or "")[:400]} for x in r.json().get("results", []) if x.get("url")]


def search(query, n=5):
    errs = []
    for name, fn in (("tavily", _tavily), ("duckduckgo", _ddg), ("mojeek", _mojeek), ("wikipedia", _wiki)):
        try:
            res = fn(query, n)
            if res:
                return res
            errs.append(f"{name}: no results")
        except Exception as e:
            errs.append(f"{name}: {type(e).__name__} {str(e)[:60]}")
    raise RuntimeError("all search providers failed: " + "; ".join(errs))
