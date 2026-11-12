"""JobMatch AI 0.2: public Greenhouse and Lever job ingestion.

Read-only job board APIs. Does not submit applications.
"""
import html
import json
import os
import re
import unicodedata
from urllib.parse import urlparse

import httpx
from supabase import create_client

MINIMUM_SAVE_SCORE = 55
SKILLS = {"php": 16, "javascript": 16, "html": 8, "css": 8, "mysql": 12,
          "sql": 8, "python": 8, "git": 8, "react": 6, "api": 5, "github": 5}
BLOCKED = ("senior", "sr", "staff", "principal", "lead", "pleno", "manager", "director", "head")
LEVELS = ("estagio", "estagiario", "intern", "internship", "junior", "jr", "trainee", "entry level", "entry-level", "graduate", "associate")
TECH = ("developer", "desenvolvedor", "desenvolvimento", "software", "programador", "frontend", "front-end", "backend", "back-end", "fullstack", "full-stack", "technology", "tecnologia", "ti", "it support", "technical support", "suporte tecnico", "help desk", "helpdesk", "service desk", "qa", "quality assurance", "test engineer", "data analyst", "analista de dados", "cybersecurity", "seguranca da informacao", "devops", "infrastructure", "infraestrutura")
BOARD_TOKEN = re.compile(r"[A-Za-z0-9_-]{2,80}\Z")


def normalize(value):
    value = re.sub(r"<[^>]*>", " ", html.unescape(str(value or "")))
    value = unicodedata.normalize("NFKD", value)
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).lower().split())


def has(text, term):
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text) is not None


def role_ok(title):
    title = normalize(title)
    return (not any(has(title, x) for x in BLOCKED)
            and any(has(title, x) for x in LEVELS)
            and any(has(title, x) for x in TECH))


def location_ok(location, description):
    loc, desc = normalize(location), normalize(description)
    if has(loc, "curitiba") or has(loc, "parana") or has(loc, "parana pr"):
        return True
    # Brazil location is only accepted if explicitly remote/hybrid in Brazil.
    brazil = any(has(loc, x) for x in ("brazil", "brasil"))
    remote = any(has(loc, x) for x in ("remote", "remoto", "work from home", "home office"))
    if brazil and remote:
        return True
    if brazil and any(has(desc, x) for x in ("remote", "remoto", "home office", "trabalho remoto")):
        return True
    if remote and any(has(desc, x) for x in ("based in brazil", "based in brasil", "remote brazil", "remote brasil", "remoto brasil", "residir no brasil", "reside in brazil")):
        return True
    return False


def score_job(title, description, location):
    if not role_ok(title) or not location_ok(location, description):
        return 0
    desc = normalize(description)
    skills = sum(weight for skill, weight in SKILLS.items() if has(desc, skill))
    return min(100, 30 + 15 + skills)


def boards_from_env(name):
    raw = os.getenv(name, "[]") or "[]"
    values = json.loads(raw)
    if not isinstance(values, list) or any(not isinstance(x, str) or not BOARD_TOKEN.fullmatch(x) for x in values):
        raise ValueError(f"{name} must be a JSON array of board tokens")
    return list(dict.fromkeys(values))


def fetch_greenhouse(client, board):
    response = client.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", params={"content": "true"})
    response.raise_for_status()
    for job in response.json().get("jobs", []):
        yield {
            "source_id": f"greenhouse:{board}:{job.get('id')}",
            "title": job.get("title") or "",
            "company": board,
            "location": (job.get("location") or {}).get("name") or "",
            "description": job.get("content") or "",
            "url": job.get("absolute_url") or "",
        }


def fetch_lever(client, board):
    # Lever public postings API (global and EU board hosts).
    base = "https://api.lever.co/v0/postings"
    response = client.get(f"{base}/{board}", params={"mode": "json"})
    response.raise_for_status()
    for job in response.json():
        categories = job.get("categories") or {}
        lists = job.get("lists") or []
        details = " ".join((item.get("content") or "") for item in lists if isinstance(item, dict))
        yield {
            "source_id": f"lever:{board}:{job.get('id')}",
            "title": job.get("text") or "",
            "company": board,
            "location": categories.get("location") or "",
            "description": " ".join([job.get("descriptionPlain") or "", job.get("additionalPlain") or "", details]),
            "url": job.get("hostedUrl") or "",
        }


def safe_url(url):
    try:
        parts = urlparse(url)
        return parts.scheme == "https" and bool(parts.netloc)
    except ValueError:
        return False


def save_job(db, job):
    # Existing rows retain their application status; only refresh match score and metadata.
    existing = db.table("jobs").select("id,status").eq("source_id", job["source_id"]).limit(1).execute().data or []
    row = {k: job[k] for k in ("source_id", "title", "company", "location", "remote", "score", "url")}
    if existing:
        db.table("jobs").update({k: v for k, v in row.items() if k != "source_id"}).eq("source_id", job["source_id"]).execute()
    else:
        row["status"] = "found"
        db.table("jobs").insert(row).execute()


def main():
    greenhouse = boards_from_env("GREENHOUSE_BOARDS")
    lever = boards_from_env("LEVER_BOARDS")
    if not greenhouse and not lever:
        print("No boards configured; exiting.")
        return
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    checked = saved = failures = 0
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for source, boards, fetcher in (("greenhouse", greenhouse, fetch_greenhouse), ("lever", lever, fetch_lever)):
            for board in boards:
                count = accepted = 0
                try:
                    for item in fetcher(client, board):
                        count += 1
                        if item["source_id"].endswith(":None") or not safe_url(item["url"]):
                            continue
                        score = score_job(item["title"], item["description"], item["location"])
                        if score < MINIMUM_SAVE_SCORE:
                            continue
                        location = normalize(item["location"])
                        item.update(title=item["title"][:250], company=item["company"][:150],
                                    location=item["location"][:250], score=score,
                                    remote=any(has(location, x) for x in ("remote", "remoto")))
                        save_job(db, item)
                        accepted += 1
                    checked += count
                    saved += accepted
                    print(f"{source}/{board}: {count} analyzed, {accepted} saved or updated")
                except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                    failures += 1
                    print(f"{source}/{board}: failed ({type(exc).__name__}: {exc})")
    print(f"Total: {checked} analyzed, {saved} saved/updated, {failures} failed boards")
    if failures:
        raise SystemExit("One or more boards failed; review logs")


if __name__ == "__main__":
    main()
