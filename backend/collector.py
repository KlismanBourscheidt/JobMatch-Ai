"""JobMatch AI 0.4: collect public Greenhouse/Lever vacancies; never apply."""
import html
import json
import os
import re
import unicodedata
from urllib.parse import urlparse

import httpx
from supabase import create_client

MINIMUM_MATCH = 50
SKILLS = {
    'php': ('php',), 'javascript': ('javascript', 'js'), 'html': ('html',),
    'css': ('css',), 'mysql': ('mysql',), 'sql': ('sql',),
    'python': ('python',), 'git': ('git',), 'github': ('github',),
    'react': ('react', 'reactjs'), 'api': ('api', 'apis', 'rest api'),
    'typescript': ('typescript',), 'node.js': ('node.js', 'nodejs'),
    'laravel': ('laravel',), 'docker': ('docker',), 'aws': ('aws',),
    'java': ('java',), 'spring': ('spring boot',), 'vue': ('vue', 'vuejs'),
    'angular': ('angular',), 'postgresql': ('postgresql', 'postgres'),
    'testing': ('unit testing', 'automated testing', 'testes automatizados', 'testes unitarios'),
    'figma': ('figma',), 'excel': ('excel',), 'linux': ('linux',),
}
# Edit as skills are confirmed; this is not proof of proficiency.
PROFILE = {'php', 'javascript', 'html', 'css', 'mysql', 'sql', 'python', 'git', 'github', 'figma'}
BLOCKED = ('senior', 'sr', 'staff', 'principal', 'lead', 'pleno', 'manager', 'director', 'head', 'architect', 'arquiteto')
ENTRY = ('estagio', 'estagiario', 'intern', 'internship', 'junior', 'jr', 'trainee', 'entry level', 'entry-level', 'graduate', 'associate', 'nivel i', 'level i', 'n1', 'apprentice', 'early career', 'new grad')
TECH = ('developer', 'desenvolvedor', 'desenvolvimento', 'software', 'programador', 'frontend', 'front-end', 'backend', 'back-end', 'fullstack', 'full-stack', 'technology', 'tecnologia', 'ti', 'it support', 'technical support', 'suporte tecnico', 'help desk', 'helpdesk', 'service desk', 'qa', 'quality assurance', 'test engineer', 'data analyst', 'analista de dados', 'cybersecurity', 'seguranca da informacao', 'devops', 'infrastructure', 'infraestrutura', 'sistemas', 'computacao', 'information technology', 'information systems', 'engenharia de software', 'engenharia de dados', 'dados', 'product engineering')
BOARD = re.compile(r'[A-Za-z0-9_-]{2,80}\Z')


def norm(value):
    text = re.sub(r'<[^>]*>', ' ', html.unescape(str(value or '')))
    text = unicodedata.normalize('NFKD', text)
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).lower().split())


def has(text, term):
    return re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text) is not None


def role_ok(title):
    title = norm(title)
    return (not any(has(title, t) for t in BLOCKED)
            and any(has(title, t) for t in ENTRY)
            and any(has(title, t) for t in TECH))


def location_ok(location, description):
    loc, desc = norm(location), norm(description)
    if any(has(loc, city) for city in ('curitiba', 'sao jose dos pinhais', 'pinhais', 'colombo', 'araucaria', 'campo largo', 'fazenda rio grande')):
        return True
    brazil = any(has(loc, t) for t in ('brazil', 'brasil'))
    remote = any(has(loc, t) for t in ('remote', 'remoto', 'home office'))
    if brazil and remote:
        return True
    if brazil and any(has(desc, t) for t in ('remote', 'remoto', 'home office', 'trabalho remoto')):
        return True
    if remote and any(has(desc, t) for t in ('based in brazil', 'based in brasil', 'remote brazil', 'remote brasil', 'remoto brasil', 'residir no brasil', 'reside in brazil')):
        return True
    return False


def skills_in(description):
    text = norm(description)
    return sorted(k for k, aliases in SKILLS.items() if any(has(text, a) for a in aliases))


def analyze(job):
    mentioned = skills_in(job['description'])
    matched = sorted(set(mentioned) & PROFILE)
    missing = sorted(set(mentioned) - PROFILE)
    # Heuristic: keywords can be optional or incidental; not a hiring probability.
    skill_points = round(50 * len(matched) / len(mentioned)) if mentioned else 0
    score = min(100, 30 + 20 + skill_points)
    recommendations = [f'Estudar {skill} e criar um pequeno projeto demonstrando seu uso.' for skill in missing[:3]]
    if not mentioned:
        recommendations = ['Revisar a descrição completa: não foram identificadas tecnologias específicas.']
    return dict(score=score, matched_skills=matched, missing_skills=missing,
                required_skills=mentioned, study_recommendations=recommendations)


def boards(name):
    values = json.loads(os.getenv(name, '[]') or '[]')
    if not isinstance(values, list) or any(not isinstance(v, str) or not BOARD.fullmatch(v) for v in values):
        raise ValueError(f'{name} deve ser uma lista JSON de identificadores')
    return list(dict.fromkeys(values))


def greenhouse(client, board):
    response = client.get(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs', params={'content': 'true'})
    response.raise_for_status()
    for item in response.json().get('jobs', []):
        yield dict(source_id=f"greenhouse:{board}:{item.get('id')}", title=item.get('title') or '',
                   company=board, location=(item.get('location') or {}).get('name') or '',
                   description=item.get('content') or '', url=item.get('absolute_url') or '')


def lever(client, board):
    response = client.get(f'https://api.lever.co/v0/postings/{board}', params={'mode': 'json'})
    response.raise_for_status()
    for item in response.json():
        categories = item.get('categories') or {}
        details = ' '.join(x.get('content') or '' for x in item.get('lists', []) if isinstance(x, dict))
        yield dict(source_id=f"lever:{board}:{item.get('id')}", title=item.get('text') or '',
                   company=board, location=categories.get('location') or '',
                   description=' '.join([item.get('descriptionPlain') or '', item.get('additionalPlain') or '', details]),
                   url=item.get('hostedUrl') or '')


def ashby(client, board):
    """Public Ashby posting API for a configured organization slug."""
    response = client.get(f'https://api.ashbyhq.com/posting-api/job-board/{board}')
    response.raise_for_status()
    for item in response.json().get('jobs', []):
        loc = item.get('location') or ''
        if isinstance(loc, dict):
            loc = loc.get('name') or ''
        description = item.get('descriptionPlain') or item.get('descriptionHtml') or ''
        yield dict(source_id=f"ashby:{board}:{item.get('id') or item.get('jobUrl')}",
                   title=item.get('title') or '', company=board,
                   location=str(loc), description=description,
                   url=item.get('jobUrl') or item.get('applyUrl') or '')


def smartrecruiters(client, board):
    """Public company postings; fetch individual posting details when available."""
    offset, limit = 0, 100
    while True:
        response = client.get(f'https://api.smartrecruiters.com/v1/companies/{board}/postings',
                              params={'offset': offset, 'limit': limit})
        response.raise_for_status()
        data = response.json()
        items = data.get('content') or []
        for item in items:
            posting_id = item.get('id')
            details = {}
            if posting_id:
                detail_response = client.get(
                    f'https://api.smartrecruiters.com/v1/companies/{board}/postings/{posting_id}')
                detail_response.raise_for_status()
                details = detail_response.json()
            location = details.get('location') or item.get('location') or {}
            if isinstance(location, dict):
                location = ', '.join(str(location.get(k) or '') for k in ('city', 'region', 'country')).strip(', ')
            sections = (details.get('jobAd') or {}).get('sections') or {}
            description = ' '.join(str(v.get('text') or '') for v in sections.values() if isinstance(v, dict))
            description += ' ' + str(details.get('description') or '')
            yield dict(source_id=f'smartrecruiters:{board}:{posting_id}',
                       title=details.get('name') or item.get('name') or '',
                       company=board, location=str(location),
                       description=description,
                       url=details.get('postingUrl') or item.get('postingUrl') or
                           f'https://jobs.smartrecruiters.com/{board}/{posting_id}')
        offset += len(items)
        if not items or len(items) < limit:
            break


def adzuna(client, country):
    """Optional Adzuna search; requires ADZUNA_APP_ID and ADZUNA_APP_KEY."""
    app_id, app_key = os.getenv('ADZUNA_APP_ID'), os.getenv('ADZUNA_APP_KEY')
    if not app_id or not app_key:
        return
    terms = ('estagio tecnologia', 'desenvolvedor junior', 'estagio desenvolvimento')
    pages = min(3, max(1, int(os.getenv('ADZUNA_PAGES', '1'))))
    for term in terms:
        for page in range(1, pages + 1):
            response = client.get(f'https://api.adzuna.com/v1/api/jobs/{country}/search/{page}',
                                  params={'app_id': app_id, 'app_key': app_key,
                                          'results_per_page': 50, 'what': term,
                                          'where': 'Curitiba', 'content-type': 'application/json'})
            response.raise_for_status()
            for item in response.json().get('results', []):
                yield dict(source_id=f"adzuna:{country}:{item.get('id')}",
                           title=item.get('title') or '',
                           company=(item.get('company') or {}).get('display_name') or 'Não informado',
                           location=(item.get('location') or {}).get('display_name') or '',
                           description=item.get('description') or '',
                           url=item.get('redirect_url') or '')


def valid_url(url):
    try:
        u = urlparse(url)
        return u.scheme == 'https' and bool(u.netloc)
    except (TypeError, ValueError):
        return False


def save(db, job, analysis):
    # Updating only selected columns preserves existing status (e.g. applied).
    existing = db.table('jobs').select('id').eq('source_id', job['source_id']).limit(1).execute().data or []
    row = {k: job[k] for k in ('title', 'company', 'location', 'remote', 'url')}
    row.update(analysis)
    if existing:
        db.table('jobs').update(row).eq('source_id', job['source_id']).execute()
        return 'updated'
    row.update(source_id=job['source_id'], status='found')
    db.table('jobs').insert(row).execute()
    return 'new'


def main():
    sources = [('greenhouse', boards('GREENHOUSE_BOARDS'), greenhouse),
               ('lever', boards('LEVER_BOARDS'), lever),
               ('ashby', boards('ASHBY_BOARDS'), ashby),
               ('smartrecruiters', boards('SMARTRECRUITERS_COMPANIES'), smartrecruiters)]
    if os.getenv('ADZUNA_APP_ID') and os.getenv('ADZUNA_APP_KEY'):
        sources.append(('adzuna', ['br'], adzuna))
    if not any(identifiers for _, identifiers, _ in sources):
        print('No boards configured; exiting.')
        return
    db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    totals = dict(analyzed=0, excluded_role=0, excluded_location=0, excluded_score=0,
                  invalid=0, new=0, updated=0, errors=0)
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for source, identifiers, fetcher in sources:
            for board in identifiers:
                stats = dict.fromkeys(totals, 0)
                try:
                    for job in fetcher(client, board):
                        stats['analyzed'] += 1
                        if job['source_id'].endswith(':None') or not valid_url(job['url']):
                            stats['invalid'] += 1
                            continue
                        if not role_ok(job['title']):
                            stats['excluded_role'] += 1
                            continue
                        if not location_ok(job['location'], job['description']):
                            stats['excluded_location'] += 1
                            continue
                        analysis = analyze(job)
                        if analysis['score'] < MINIMUM_MATCH:
                            stats['excluded_score'] += 1
                            continue
                        loc = norm(job['location'])
                        job.update(title=job['title'][:250], company=job['company'][:150],
                                   location=job['location'][:250],
                                   remote=any(has(loc, t) for t in ('remote', 'remoto')))
                        stats[save(db, job, analysis)] += 1
                except (httpx.HTTPError, ValueError, KeyError, TypeError, RuntimeError) as exc:
                    stats['errors'] += 1
                    print(f'{source}/{board}: ERROR {type(exc).__name__}: {exc}')
                for key in totals:
                    totals[key] += stats[key]
                print(f'{source}/{board}: ' + ' '.join(f'{key}={value}' for key, value in stats.items()))
    print('TOTAL: ' + ' '.join(f'{key}={value}' for key, value in totals.items()))
    if totals['errors']:
        raise SystemExit('Falha em uma ou mais fontes; consulte os logs')


if __name__ == '__main__':
    main()
