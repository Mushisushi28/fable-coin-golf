# Leaderboards & achievements without Xbox Live

Xbox Live for Windows Phone is gone, and so is the Fable III cloud
service the game posted gold transfers to. The port replaces both
behind the game's *original* wrapper APIs, so no gameplay code
changes: consumers proceed only inside callbacks, exactly as designed
— the backends just answer locally and synchronously. On top of that,
the port adds a **global** leaderboard layer that the dead Live
service used to provide.

## The local backend (`src/scaffold/compat/`)

- **Identity:** one process-wide local profile. The in-game name is
  the constant `"YOU"` — self-evidently a personal board, short enough
  for the game's narrow name column.
- **Sign-in:** the callback fires synchronously, in the same call
  stack, with the local gamer. This is the entire fix for the dead
  "SYNCING…" screens (see `docs/FIXES.md`).
- **Achievements:** reads return fresh snapshot copies of the save's
  own achievement array — **never null** (a null read is the error
  signal in the game's sync code and throws once any earn exists).
  Writes commit the whole save to disk at the moment an achievement
  earns, so mid-level earns can't be lost to an app kill.
- **Leaderboards:** there is no local store and no fabricated data.
  Reads are synthesised at read time from the player's own per-level
  best scores, which the game already tracks and persists:
  - board IDs 0–3: chapter/overall boards — per-level personal bests
    in scope, best first, ties in campaign order, plus a pivot row
    with the player's total;
  - board IDs 4–48: per-level boards — the single row for that level,
    showing `max(best score, current total)` so a just-finished level
    never displays a stale best.
  Writes are accept-and-report-success: the game's level-end writes
  exactly mirror state it persists itself, so a second store would
  only add a way to disagree.
- **The one semantic exception:** the `sent_gold` achievement
  originally meant "sent gold to Fable III" over a service that no
  longer exists. Locally it is reinterpreted as *banking* gold at
  level end, and the two in-game strings describing it are reworded
  accordingly by `patcher/patch_resx.py`.
- **Cloud service:** `compat/CCloudConnectivity.cs` keeps every
  public signature of the original and performs no network I/O at
  all. Avatar fetches answer with a null texture, which both UIs
  treat as "keep the template image".

### What local boards can never do
No cross-player or cross-device comparison, no rank against anyone
else, no Xbox identity/Gamerscore/avatar, no actual Fable III
transfers, no cloud saves. Scores live in a plaintext XML save on the
device — fine for personal bests, meaningless as proof.

## The global backend (included — bring your own host)

The newest development builds replaced the leaderboard *surfaces*
with global boards. That client is included here in full:
`src/scaffold/CLeaderboardService.cs`, wired in by the in-place
patches to the leaderboard/options/level-end states (see
`patches/PATCHES.md`). It talks to a hosted Postgres database
(Supabase) over its REST/RPC interface — **your** project, not
anyone else's: no project reference, endpoint, or key of any live
service appears in this repository.

### Set it up

1. Create a free Supabase project (or use any Postgres + PostgREST
   host that matches the contract below).
2. Run `docs/supabase-schema.sql` in its SQL editor. It creates the
   `players` and `scores` tables and the three functions the client
   calls:
   - `submit_score(p_username, p_secret, p_board, p_score)` — upsert
     the player's best; requires the per-device secret generated at
     claim time, returns boolean;
   - `get_leaderboard(p_board, p_limit)` — top rows
     `{rank, username, score}` for a board;
   - `get_player_rank(p_board, p_username)` — the player's row.
   Claiming a username is a direct insert into `players` (201 on
   success, 409 when the name is taken).
3. Copy `leaderboard.config.example.json` to
   `leaderboard.config.json` (git-ignored), fill in your project URL
   and **anon** key, and re-run the patcher. It generates the work
   tree's `LeaderboardConfig.cs` from it. Never use a service-role
   key: the anon key is public by design and ships in the app; the
   schema's security model (row-level security + the secret check in
   `submit_score`) is written for exactly that.

Boards are named `overall`, `chapter1`…`chapter3`, and `level:<id>`.

### Identity

The username is claimed in Settings through a native Android dialog
(`Activity1.cs` + `src/resources/layout/dialog_username.xml`).
Identity (username + per-device secret) is stored in its own
`identity.dat` next to the save — **not** in the game save — so an
in-app data reset keeps the username and the scores submitted under
it, and claiming a username backfills every score earned before the
claim (the save itself is the backfill queue; `submit_score` keeps
the max, so re-running is safe).

### When no backend is configured

This is the default, and it is a complete configuration, not an
error: `CLeaderboardService` detects the empty config and serves
every board read from `LocalLeaderboards` (same board mapping), score
submits become no-ops, and username claims report an error in the
dialog. The game is fully playable offline and the leaderboard
screens show your personal-best boards.
