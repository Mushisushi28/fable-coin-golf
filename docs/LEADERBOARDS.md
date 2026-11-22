# Leaderboards & achievements without Xbox Live

Xbox Live for Windows Phone is gone, and so is the Fable III cloud
service the game posted gold transfers to. The port replaces both
behind the game's *original* wrapper APIs, so no gameplay code
changes: consumers proceed only inside callbacks, exactly as designed
— the backends just answer locally and synchronously.

## Included: the local backend (`src/scaffold/compat/`)

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
  accordingly in the development builds (the reworded resource file
  is a modified game resource, so it is not distributed here; the
  local-backend behaviour is in `compat/CCloudConnectivity.cs`).
- **Cloud service:** `compat/CCloudConnectivity.cs` keeps every
  public signature of the original and performs no network I/O at
  all. Avatar fetches answer with a null texture, which both UIs
  treat as "keep the template image".

### What local boards can never do
No cross-player or cross-device comparison, no rank against anyone
else, no Xbox identity/Gamerscore/avatar, no actual Fable III
transfers, no cloud saves. Scores live in a plaintext XML save on the
device — fine for personal bests, meaningless as proof.

## Optional: your own global backend (interface spec)

The later development builds added global boards on top of the same
wrapper, backed by a hosted Postgres database (Supabase) accessed over
its REST/RPC interface. That client was written against one specific
hosted project, so it is **not included in this repository** — no
project reference, endpoint, or key of any live service appears here.
To build your own equivalent you need:

- a table of scores keyed by a player-chosen username, level/board
  id, and score;
- three RPC-style functions with these contracts:
  - `submit_score(username, board, score)` — upsert the player's best;
  - `get_leaderboard(board, count)` — top rows for a board;
  - `get_player_rank(username, board)` — the player's row and rank;
- a client in the scaffold that calls them with **your own** project
  URL and anon key, kept in a local, git-ignored config file — never
  committed;
- identity stored separately from the game save (the development
  builds used a small `identity.dat` next to the save, with a
  username-claim field in Settings), so resetting game data keeps the
  player's username and previously submitted scores, and claiming a
  username backfills scores earned before the claim.

Until you build that, the local backend above is the complete,
offline-correct behaviour.
