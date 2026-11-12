'''Scheduled Greenhouse job ingestion. Only public read-only API; no applications sent.'''
import os
import re
import json
import httpx
from supabase import create_client

MINIMUM_MATCH = 80
SKILLS = {'php': 16, 'javascript': 16, 'html': 8, 'css': 8, 'mysql': 12,
          'sql': 8, 'python': 8, 'git': 8, 'react': 6, 'api': 5, 'github': 5}
BLOCKED = ('senior', 'sênior', 'sr.', 'staff', 'principal', 'lead', 'pleno')
TARGET = ('estágio', 'estagiário', 'intern', 'junior', 'júnior', 'jr.', 'trainee')
def score_job(title, description, location):
    title_l=title.lower()
    desc=re.sub(r'<[^>]*>', ' ', description).lower()
    loc=location.lower()
    if any(x in title_l for x in BLOCKED):
        return 0
    if not any(x in title_l for x in TARGET):
        return 0
    # Strictly a heuristic ranking, not a statistical probability.
    # High scores require matching role + multiple skills + location evidence.
    role=30
    skill_points=sum(weight for skill,weight in SKILLS.items() if re.search(r'(?<!\\w)'+re.escape(skill)+r'(?!\\w)', desc))
    place=15 if any(x in loc for x in ('curitiba','brazil','brasil','remote','remoto')) else 0
    return min(100, role+skill_points+place)
def is_target_location(location,description):
    text=(location+' '+description[:2000]).lower()
    return any(x in text for x in ('curitiba','brazil','brasil','remote - brazil','remoto - brasil','remote brazil','remoto brasil'))
def main():
    db=create_client(os.environ['SUPABASE_URL'],os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    boards=json.loads(os.getenv('GREENHOUSE_BOARDS','[]'))
    if not boards:
        print('No Greenhouse boards configured; exiting without changes.')
        return
    with httpx.Client(timeout=25,follow_redirects=True) as client:
        for board in boards:
            if not re.fullmatch(r'[a-zA-Z0-9_-]{2,80}',board):
                print('Skipping invalid board token')
                continue
            try:
                resp=client.get(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs',params={'content':'true'})
                resp.raise_for_status()
                for job in resp.json().get('jobs',[]):
                    title=job.get('title','')
                    location=(job.get('location') or {}).get('name','')
                    description=job.get('content','')
                    if not is_target_location(location,description):
                        continue
                    points=score_job(title,description,location)
                    if points < MINIMUM_MATCH:
                        continue
                    url=job.get('absolute_url','')
                    if not url.startswith('https://'):
                        continue
                    row={'source_id':f'greenhouse:{board}:{job["id"]}',
                         'title':title[:250], 'company':board[:150],
                         'location':location[:250], 'remote':'remote' in location.lower() or 'remoto' in location.lower(),
                         'score':points,'status':'found','url':url}
                    db.table('jobs').upsert(row,on_conflict='source_id').execute()
                print('Processed board:',board)
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                print('Failed board:',board,str(exc))
if __name__=='__main__':
    main()
