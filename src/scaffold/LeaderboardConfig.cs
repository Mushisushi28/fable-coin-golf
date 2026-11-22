// LeaderboardConfig - your global-leaderboard backend settings.
//
// This file ships with EMPTY values: the game then uses the local
// personal-best leaderboards and makes no network calls (see
// docs/LEADERBOARDS.md). To use your own hosted backend, do NOT edit
// your settings into a copy you might commit - instead create
// leaderboard.config.json at the repository root (copy
// leaderboard.config.example.json) and re-run the patcher: it
// regenerates this file in your work tree with your values.
// leaderboard.config.json is git-ignored.
//
// The anon key is public by design for this kind of backend (it ships
// in the app; access is governed by row-level security and the
// submit_score secret check - see docs/supabase-schema.sql). Never
// put a service-role / admin key here.
public static class LeaderboardConfig
{
	public const string SupabaseUrl = "";
	public const string AnonKey = "";
}
