create table if not exists public.jobs (
 id bigint generated always as identity primary key,
 source_id text not null unique,
 title text not null,
 company text not null,
 location text not null default '',
 remote boolean not null default false,
 score integer not null check (score between 0 and 100),
 status text not null default 'found' check (status in ('found','review','applied','failed')),
 url text not null,
 created_at timestamptz not null default now()
);
create index if not exists jobs_score_idx on public.jobs(score desc);
alter table public.jobs enable row level security;
-- No policies: browser clients cannot query the table.
-- Only the FastAPI backend and scheduled collector use the server-side service-role key.
revoke all on table public.jobs from anon, authenticated;
revoke all on sequence public.jobs_id_seq from anon, authenticated;
