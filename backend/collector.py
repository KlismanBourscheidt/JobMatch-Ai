
"""
JobMatch AI - Coletor automático de vagas.

Consulta vagas públicas do Greenhouse,
classifica oportunidades e salva no Supabase.

Não realiza candidaturas automáticas.
"""

import os
import re
import json
import html
import unicodedata

import httpx
from supabase import create_client


MINIMUM_MATCH = 80

SKILLS = {
    "php": 16,
    "javascript": 16,
    "html": 8,
    "css": 8,
    "mysql": 12,
    "sql": 8,
    "python": 8,
    "git": 8,
    "react": 6,
    "api": 5,
    "github": 5,
}

BLOCKED = (
    "senior",
    "sr.",
    "staff",
    "principal",
    "lead",
    "pleno",
    "manager",
    "director",
)

TARGET = (
    "estagio",
    "estagiario",
    "intern",
    "internship",
    "junior",
    "jr.",
    "trainee",
)

TECH_ROLES = (
    "developer",
    "desenvolvedor",
    "desenvolvimento",
    "software engineer",
    "engenheiro de software",
    "programador",
    "web development",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "fullstack",
    "full-stack",
    "technology",
    "tecnologia",
    "engineering intern",
    "engenharia de software",
)

BRAZIL_LOCATIONS = (
    "curitiba",
    "parana",
    "brazil",
    "brasil",
)


def normalize(text):
    text = html.unescape(str(text or ""))

    text = re.sub(r"<[^>]*>", " ", text)

    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )

    return text.lower().strip()


def contains_term(text, term):
    return re.search(
        r"(?<!\w)" + re.escape(term) + r"(?!\w)",
        text
    ) is not None


def is_target_role(title):
    title = normalize(title)

    if any(
        contains_term(title, term)
        for term in BLOCKED
    ):
        return False

    if not any(
        contains_term(title, term)
        for term in TARGET
    ):
        return False

    return any(
        term in title
        for term in TECH_ROLES
    )


def is_target_location(location, description=""):
    loc = normalize(location)
    desc = normalize(description)

    if any(
        place in loc
        for place in BRAZIL_LOCATIONS
    ):
        return True

    remote_terms = (
        "remote brazil",
        "remote - brazil",
        "remote brasil",
        "remoto brasil",
        "remoto - brasil",
        "remote within brazil",
    )

    if any(term in loc for term in remote_terms):
        return True

    # Localização remota com restrição explícita ao Brasil
    if "remote" in loc or "remoto" in loc:
        return any(
            term in desc
            for term in (
                "remote brazil",
                "remote brasil",
                "remoto brasil",
                "based in brazil",
                "residir no brasil",
            )
        )

    return False


def score_job(title, description, location):
    if not is_target_role(title):
        return 0

    if not is_target_location(location, description):
        return 0

    desc = normalize(description)

    # Pontuação por perfil da vaga
    role_points = 30

    # Pontuação pelas habilidades identificadas
    skill_points = sum(
        weight
        for skill, weight in SKILLS.items()
        if contains_term(desc, skill)
    )

    # Pontuação por localização
    location_points = 15

    return min(
        100,
        role_points + skill_points + location_points
    )


def main():
    print("Iniciando coletor JobMatch AI...")

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    db = create_client(
        supabase_url,
        supabase_key
    )

    boards = json.loads(
        os.getenv("GREENHOUSE_BOARDS", "[]")
    )

    if not isinstance(boards, list):
        raise ValueError(
            "GREENHOUSE_BOARDS deve ser uma lista JSON."
        )

    if not boards:
        print(
            "Nenhuma empresa Greenhouse configurada."
        )
        return

    total_found = 0
    total_saved = 0

    with httpx.Client(
        timeout=25,
        follow_redirects=True
    ) as client:

        for board in boards:

            if (
                not isinstance(board, str)
                or not re.fullmatch(
                    r"[a-zA-Z0-9_-]{2,80}",
                    board
                )
            ):
                print("Identificador de empresa inválido.")
                continue

            print(f"Consultando empresa: {board}")

            try:

                response = client.get(
                    f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
                    params={"content": "true"}
                )

                response.raise_for_status()

                jobs = response.json().get("jobs", [])

                for job in jobs:

                    total_found += 1

                    title = job.get("title") or ""

                    location = (
                        job.get("location") or {}
                    ).get("name") or ""

                    description = job.get("content") or ""

                    if not is_target_role(title):
                        continue

                    if not is_target_location(
                        location,
                        description
                    ):
                        continue

                    score = score_job(
                        title,
                        description,
                        location
                    )

                    if score < MINIMUM_MATCH:
                        continue

                    job_url = job.get("absolute_url") or ""

                    if not job_url.startswith("https://"):
                        continue

                    job_id = job.get("id")

                    if job_id is None:
                        continue

                    row = {
                        "source_id": (
                            f"greenhouse:{board}:{job_id}"
                        ),
                        "title": title[:250],
                        "company": board[:150],
                        "location": location[:250],
                        "remote": (
                            "remote" in normalize(location)
                            or "remoto" in normalize(location)
                        ),
                        "score": score,
                        "status": "found",
                        "url": job_url,
                    }

                    db.table("jobs").upsert(
                        row,
                        on_conflict="source_id"
                    ).execute()

                    total_saved += 1

                print(
                    f"Empresa {board}: "
                    f"{len(jobs)} vagas consultadas."
                )

            except (
                httpx.HTTPError,
                ValueError,
                KeyError
            ) as error:

                print(
                    f"Erro ao consultar {board}: {error}"
                )

    print("Coleta finalizada.")
    print(f"Vagas analisadas: {total_found}")
    print(f"Vagas gravadas: {total_saved}")


if __name__ == "__main__":
    main()
