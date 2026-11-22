// ACH/LB local backend — personal-best leaderboard provider.
// STAGED 2026-11-14 (implementation prep per ACH-LB-PLAN.md §2.2). NOT yet in
// srcC: drops into FableCoinGolf.Android\ alongside the rewritten
// XboxLiveStub.cs when the ACH/LB implementation phase starts.
//
// Design (plan §2.2): the only data source is the player's own
// CPlayerInfo.GameScores — the same live object the game restores from
// game.sav at load and updates in play. No separate leaderboard store, no
// fake players, no fabricated scores. Reads are synthesized at read time;
// the game's level-end WriteLeaderboard calls are pure mirrors of
// GameScores state and are accepted without storage by the wrapper.
//
// Contract rules (both UIs depend on them):
//   - NEVER return null: null is the error signal in both consumers
//     (menu -> LEADERBOARD_NO_SERVER panel + chain stop; level end ->
//     m_SyncingFailed). Empty list is the honest "no scores yet" state and
//     renders the game's built-in placeholder row + chicken.
//   - Handlers are invoked synchronously by the wrapper; this provider is
//     pure allocation + arithmetic and never throws (defensive catch ->
//     empty list).
using System;
using System.Collections.Generic;
using System.Linq;

public static class LocalLeaderboards
{
	// The local profile name (plan §2.2): device-neutral, self-evidently a
	// personal board, short enough for the narrow name column.
	public const string LocalPlayerName = "YOU";

	public static List<CLeaderboardEntry> Read(int variationId, bool pivotGamer, int count)
	{
		try
		{
			if (count <= 0)
			{
				return new List<CLeaderboardEntry>();
			}
			if (variationId >= 0 && variationId <= 3)
			{
				return pivotGamer ? ReadPivotTotal(variationId) : ReadTopRows(variationId, count);
			}
			if (variationId >= 4 && variationId <= 48)
			{
				// Per-level boards feed only the level-end panel, which never
				// issues pivot reads; a pivot request here gets the same row.
				return ReadLevelRow(variationId);
			}
			return new List<CLeaderboardEntry>();
		}
		catch
		{
			// Never throw into the game, never return null (see header).
			return new List<CLeaderboardEntry>();
		}
	}

	// Menu boards (variationId 0..3), top read: per-level personal bests for
	// the board's scope, best first. Tag carries the level's display name —
	// the fixed row UI has no level field, so the name column is the only
	// honest way to distinguish same-player rows (plan §2.2).
	private static List<CLeaderboardEntry> ReadTopRows(int boardId, int count)
	{
		List<CLeaderboardEntry> rows = new List<CLeaderboardEntry>();
		GameScores scores = CPlayerInfo.GameScores;
		if (scores == null || CSettings.LevelTable == null)
		{
			return rows;
		}
		List<CLevelManager.LevelData.Chapter> chapters = ScopeChapters(boardId);
		// Collect in campaign order first; OrderByDescending is a stable
		// sort, so ties keep campaign order (deterministic, plan §2.2).
		List<KeyValuePair<string, int>> bests = new List<KeyValuePair<string, int>>();
		foreach (CLevelManager.LevelData.Chapter chapter in chapters)
		{
			foreach (CLevelManager.LevelData.Level level in chapter.Levels)
			{
				CLevelScores levelScores = scores.FindLevel(level.Name, false);
				int best = (levelScores != null) ? levelScores.BestScore : 0;
				if (best > 0)
				{
					bests.Add(new KeyValuePair<string, int>(level.GetLocalisationString(), best));
				}
			}
		}
		int pos = 1;
		foreach (KeyValuePair<string, int> entry in bests.OrderByDescending(pair => pair.Value).Take(count))
		{
			rows.Add(new CLeaderboardEntry { Pos = pos++, Tag = entry.Key, Score = entry.Value });
		}
		return rows;
	}

	// Menu boards, pivot read (count = 1): the player's aggregate entry for
	// the board, preserving the aggregate semantics the game itself writes
	// on level end (Overall total / chapter total). One row, or empty when
	// the total is 0.
	private static List<CLeaderboardEntry> ReadPivotTotal(int boardId)
	{
		List<CLeaderboardEntry> rows = new List<CLeaderboardEntry>();
		GameScores scores = CPlayerInfo.GameScores;
		if (scores == null || CSettings.LevelTable == null)
		{
			return rows;
		}
		int total;
		if (boardId == 0)
		{
			total = scores.GetOverallTotalScore();
		}
		else
		{
			// Chapter total = sum of the chapter's level bests, identical to
			// CChapterScores.GetScore() (computed directly to avoid relying
			// on the chapter-name keying of GameScores.GetChapter).
			total = 0;
			foreach (CLevelManager.LevelData.Level level in ScopeChapters(boardId)[0].Levels)
			{
				CLevelScores levelScores = scores.FindLevel(level.Name, false);
				if (levelScores != null)
				{
					total += levelScores.BestScore;
				}
			}
		}
		if (total > 0)
		{
			rows.Add(new CLeaderboardEntry { Pos = 1, Tag = LocalPlayerName, Score = total });
		}
		return rows;
	}

	// Level-end board (variationId = level ID, 4..48): the player's row for
	// that level. Timing rule (plan §2.2): the level-end read runs BEFORE
	// CLevelScores.UpdateBestScore(), so the effective best is
	// max(BestScore, GetTotalScore()) — GetTotalScore() is the just-finished
	// run's total on the level being ended, and can only raise the value to
	// the run's actual result. Empty when the effective best is 0.
	private static List<CLeaderboardEntry> ReadLevelRow(int levelId)
	{
		List<CLeaderboardEntry> rows = new List<CLeaderboardEntry>();
		GameScores scores = CPlayerInfo.GameScores;
		if (scores == null)
		{
			return rows;
		}
		CLevelScores levelScores = scores.FindLevel(levelId, false);
		if (levelScores == null)
		{
			return rows;
		}
		int effectiveBest = Math.Max(levelScores.BestScore, levelScores.GetTotalScore());
		if (effectiveBest > 0)
		{
			rows.Add(new CLeaderboardEntry { Pos = 1, Tag = LocalPlayerName, Score = effectiveBest });
		}
		return rows;
	}

	// Board scope: 0 = all chapters; 1..3 = that chapter alone.
	private static List<CLevelManager.LevelData.Chapter> ScopeChapters(int boardId)
	{
		List<CLevelManager.LevelData.Chapter> all = CSettings.LevelTable.AllChapters;
		if (boardId == 0)
		{
			return all;
		}
		List<CLevelManager.LevelData.Chapter> single = new List<CLevelManager.LevelData.Chapter>();
		if (boardId - 1 < all.Count)
		{
			single.Add(all[boardId - 1]);
		}
		return single;
	}
}
