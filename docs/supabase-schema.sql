-- Global leaderboard backend for the Fable: Coin Golf port.
--
-- A from-spec implementation of the backend contract in
-- docs/LEADERBOARDS.md, for Supabase (hosted Postgres + PostgREST).
-- Run it in your own project's SQL editor, then put your project URL
-- and anon key in leaderboard.config.json (see
-- leaderboard.config.example.json) and re-run the patcher.
--
-- Contract implemented:
--   POST /rest/v1/players            {username, device_secret} -> 201,
--                                    409 when the username is taken
--   RPC  submit_score   (p_username, p_secret, p_board, p_score)
--                        -> boolean (true when accepted)
--   RPC  get_leaderboard(p_board, p_limit)
--                        -> [{rank, username, score}] best first
--   RPC  get_player_rank(p_board, p_username)
--                        -> [{rank, username, score}] (0 or 1 rows)
--
-- Security model (matches the client): the anon key is public and
-- ships in the app. Direct table access is locked down (no policies
-- for the anon role below the grants); all reads/writes go through
-- the three functions, and submit_score requires the per-device
-- secret generated when the username was claimed. This stops casual
-- forgery, not a determined reverse-engineer - leaderboards here are
-- for fun, not prizes.

create table if not exists public.players (
    username      text primary key check (username ~ '^[A-Za-z0-9_]{3,16}$'),
    device_secret text not null,
    created_at    timestamptz not null default now()
);

create table if not exists public.scores (
    username   text not null references public.players(username) on delete cascade,
    board      text not null,
    score      integer not null,
    updated_at timestamptz not null default now(),
    primary key (username, board)
);

alter table public.players enable row level security;
alter table public.scores  enable row level security;

-- The client inserts directly into players to claim a username
-- (PostgREST returns 201, or 409 on the primary-key conflict, which
-- the client maps to "username taken"). Inserts only: the anon role
-- can never read device_secret back, and there is no update/delete.
drop policy if exists players_insert_anon on public.players;
create policy players_insert_anon on public.players
    for insert to anon, authenticated
    with check (true);

grant insert on public.players to anon, authenticated;
-- No grants on scores: the functions below are security definer and
-- are the only path in or out.

create or replace function public.submit_score(
    p_username text, p_secret text, p_board text, p_score integer)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (select 1 from players
                   where username = p_username
                     and device_secret = p_secret) then
        return false;
    end if;
    insert into scores (username, board, score)
    values (p_username, p_board, p_score)
    on conflict (username, board) do update
        set score = greatest(scores.score, excluded.score),
            updated_at = now();
    return true;
end;
$$;

create or replace function public.get_leaderboard(p_board text, p_limit integer)
returns table (rank bigint, username text, score integer)
language sql
security definer
set search_path = public
as $$
    select row_number() over (order by s.score desc, s.username asc) as rank,
           s.username, s.score
    from scores s
    where s.board = p_board
    order by s.score desc, s.username asc
    limit greatest(1, least(p_limit, 100));
$$;

create or replace function public.get_player_rank(p_board text, p_username text)
returns table (rank bigint, username text, score integer)
language sql
security definer
set search_path = public
as $$
    with ranked as (
        select row_number() over (order by s.score desc, s.username asc) as rank,
               s.username, s.score
        from scores s
        where s.board = p_board
    )
    select * from ranked where username = p_username;
$$;

grant execute on function public.submit_score(text, text, text, integer)
    to anon, authenticated;
grant execute on function public.get_leaderboard(text, integer)
    to anon, authenticated;
grant execute on function public.get_player_rank(text, text)
    to anon, authenticated;
