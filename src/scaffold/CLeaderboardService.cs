// CLeaderboardService - global leaderboard backend for the port.
//
// Replaces the dead Xbox Live leaderboard path with a hosted Postgres
// backend (Supabase / PostgREST) that YOU configure: see
// docs/LEADERBOARDS.md for the backend setup (docs/supabase-schema.sql)
// and leaderboard.config.example.json for the configuration file. No
// project URL or key for any live service is included in this
// repository; the values come from LeaderboardConfig, which the
// patcher generates from your own leaderboard.config.json.
//
// When no backend is configured, every read falls back to the local
// personal-best boards (LocalLeaderboards) and username claims report
// an error, so the game is fully playable offline - the global boards
// are strictly opt-in per builder.
//
// Design notes:
// - The anon key of a Supabase-style project is public by design
//   (such keys ship in client apps; row-level security + the
//   submit_score function's per-device secret check are what protect
//   the data). A service-role key must never be put in the config.
// - Identity (username + per-device secret GUID) lives in its own
//   isolated-storage file, identity.dat. It is NEVER inside game.sav
//   and EraseSaveFile() never touches it, so an in-app data reset
//   keeps the claimed username and all cloud scores submitted under it.
// - Scores earned before a username exists stay local in game.sav; the
//   first successful claim backfills them (game.sav IS the queue).
// - All HTTP runs on background threads. Callbacks only assign data
//   fields / set flags; every UI rebuild happens on the game thread
//   via the consumers' existing m_NeedsRefresh / Update() machinery.
// - No part of the old cloud service's HMAC signing is reused: the
//   hardcoded HMAC key in the original file must never be used for
//   auth. The only credential here is the per-device secret generated
//   at claim time.
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.IsolatedStorage;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

public static class CLeaderboardService
{
	public enum ClaimResult
	{
		Success,
		Taken,
		Invalid,
		Error
	}

	// Backend endpoint + anon key, from LeaderboardConfig (generated
	// by the patcher from your leaderboard.config.json; empty when no
	// backend is configured).
	private static string SupabaseUrl => LeaderboardConfig.SupabaseUrl;
	private static string AnonKey => LeaderboardConfig.AnonKey;

	// True when the builder configured their own backend. When false,
	// reads serve the local personal-best boards instead and claims
	// report ClaimResult.Error.
	public static bool Configured =>
		!string.IsNullOrEmpty(SupabaseUrl) && !string.IsNullOrEmpty(AnonKey);

	private const string IdentityFileName = "identity.dat";

	public const string BoardOverall = "overall";

	private static readonly HttpClient s_Http = CreateHttpClient();

	private static readonly Regex s_UsernamePattern = new Regex("^[A-Za-z0-9_]+$", RegexOptions.Compiled);

	// Identity, loaded once at first use. device_secret is a GUID
	// generated at claim time; it is the only credential for writes.
	private static string s_Username;
	private static string s_DeviceSecret;
	private static bool s_IdentityLoaded;

	// Set when a claim succeeds; consumed by the Settings screen's
	// Update() to refresh the username button text.
	private static bool s_UsernameChanged;

	private static HttpClient CreateHttpClient()
	{
		HttpClient client = new HttpClient();
		client.Timeout = TimeSpan.FromSeconds(10);
		if (Configured)
		{
			client.DefaultRequestHeaders.Add("apikey", AnonKey);
			client.DefaultRequestHeaders.Add("Authorization", "Bearer " + AnonKey);
		}
		return client;
	}

	public static string BoardForMenu(int leaderboardId)
	{
		return leaderboardId == 0 ? BoardOverall : "chapter" + leaderboardId;
	}

	public static string BoardForLevel(int levelId)
	{
		return "level:" + levelId;
	}

	public static string BoardForChapter(int chapterId)
	{
		return "chapter" + chapterId;
	}

	public static bool HasUsername
	{
		get
		{
			EnsureIdentityLoaded();
			return !string.IsNullOrEmpty(s_Username);
		}
	}

	public static string Username
	{
		get
		{
			EnsureIdentityLoaded();
			return s_Username ?? "";
		}
	}

	// Settings screen polls this in Update(); true only once per claim.
	public static bool ConsumeUsernameChanged()
	{
		bool changed = s_UsernameChanged;
		s_UsernameChanged = false;
		return changed;
	}

	public static string ValidateUsername(string name)
	{
		if (name == null)
		{
			return null;
		}
		string trimmed = name.Trim();
		if (trimmed.Length < 3 || trimmed.Length > 16)
		{
			return null;
		}
		if (!s_UsernamePattern.IsMatch(trimmed))
		{
			return null;
		}
		return trimmed;
	}

	// ---- identity storage (separate file, never game.sav) ----

	private static void EnsureIdentityLoaded()
	{
		if (s_IdentityLoaded)
		{
			return;
		}
		s_IdentityLoaded = true;
		try
		{
			using (IsolatedStorageFile store = IsolatedStorageFile.GetUserStoreForApplication())
			{
				if (!store.FileExists(IdentityFileName))
				{
					return;
				}
				using (IsolatedStorageFileStream stream = store.OpenFile(IdentityFileName, FileMode.Open))
				{
					using (StreamReader reader = new StreamReader(stream))
					{
						string username = reader.ReadLine();
						string secret = reader.ReadLine();
						if (!string.IsNullOrEmpty(username) && !string.IsNullOrEmpty(secret))
						{
							s_Username = username;
							s_DeviceSecret = secret;
						}
					}
				}
			}
		}
		catch
		{
			// A corrupt identity file must never break the game: the
			// player simply has no username until they claim one.
			s_Username = null;
			s_DeviceSecret = null;
		}
	}

	private static void SaveIdentity(string username, string deviceSecret)
	{
		s_Username = username;
		s_DeviceSecret = deviceSecret;
		try
		{
			using (IsolatedStorageFile store = IsolatedStorageFile.GetUserStoreForApplication())
			{
				using (IsolatedStorageFileStream stream = store.OpenFile(IdentityFileName, FileMode.Create))
				{
					using (StreamWriter writer = new StreamWriter(stream))
					{
						writer.WriteLine(username);
						writer.WriteLine(deviceSecret);
					}
				}
			}
		}
		catch
		{
			// Identity is held in memory for this session even if the
			// write failed; the next claim re-saves it.
		}
	}

	// ---- username dialog (native Android, via Activity1) ----

	public static void BeginUsernameChange()
	{
		try
		{
			FableCoinGolf.Android.Activity1 activity = FableCoinGolf.Android.Activity1.Instance;
			if (activity == null)
			{
				return;
			}
			activity.ShowUsernameDialog(Username, OnDialogSubmitted, OnDialogCancelled);
		}
		catch
		{
		}
	}

	// Invoked on the Android UI thread when the player taps Save with a
	// locally-valid name. The dialog stays open showing "Checking..."
	// until the claim result comes back.
	private static void OnDialogSubmitted(string name)
	{
		string valid = ValidateUsername(name);
		if (valid == null)
		{
			FableCoinGolf.Android.Activity1.Instance.FinishUsernameDialog(ClaimResult.Invalid);
			return;
		}
		ClaimUsername(valid, OnClaimFinished);
	}

	private static void OnDialogCancelled()
	{
		// Nothing to do: no identity change, no network call.
	}

	// Invoked on a background thread when the claim HTTP completes.
	private static void OnClaimFinished(ClaimResult result)
	{
		try
		{
			FableCoinGolf.Android.Activity1 activity = FableCoinGolf.Android.Activity1.Instance;
			if (activity != null)
			{
				activity.RunOnUiThread(delegate
				{
					activity.FinishUsernameDialog(result);
				});
			}
		}
		catch
		{
		}
	}

	// ---- claim + backfill ----

	public static void ClaimUsername(string name, Action<ClaimResult> callback)
	{
		if (!Configured)
		{
			callback?.Invoke(ClaimResult.Error);
			return;
		}
		string valid = ValidateUsername(name);
		if (valid == null)
		{
			callback?.Invoke(ClaimResult.Invalid);
			return;
		}
		Task.Run(async delegate
		{
			ClaimResult result = await ClaimUsernameAsync(valid);
			callback?.Invoke(result);
		});
	}

	private static async Task<ClaimResult> ClaimUsernameAsync(string username)
	{
		// A fresh secret per claim: the old secret (if any) belongs to
		// the previous username and its scores stay under that name.
		string secret = Guid.NewGuid().ToString();
		try
		{
			string json = JsonSerializer.Serialize(new
			{
				username = username,
				device_secret = secret
			});
			using (StringContent content = new StringContent(json, Encoding.UTF8, "application/json"))
			{
				using (HttpResponseMessage response = await s_Http.PostAsync(SupabaseUrl + "/rest/v1/players", content))
				{
					if ((int)response.StatusCode == 201)
					{
						SaveIdentity(username, secret);
						s_UsernameChanged = true;
						// Backfill runs in the background; the claim
						// itself is already done.
						Task.Run(delegate { BackfillScoresAsync(); });
						return ClaimResult.Success;
					}
					if ((int)response.StatusCode == 409)
					{
						return ClaimResult.Taken;
					}
					return ClaimResult.Error;
				}
			}
		}
		catch
		{
			return ClaimResult.Error;
		}
	}

	// Scores earned before a username existed, submitted under the new
	// name. game.sav IS the queue: every non-zero local best, every
	// chapter total and the overall total. submit_score keeps the max,
	// so re-running this is safe.
	private static async Task BackfillScoresAsync()
	{
		try
		{
			GameScores scores = CPlayerInfo.GameScores;
			if (scores == null || !HasUsername)
			{
				return;
			}
			CGameSaveData.LevelProgressSaveData[] progress = scores.GetGameProgress();
			if (progress == null)
			{
				return;
			}
			HashSet<string> chaptersSeen = new HashSet<string>();
			foreach (CGameSaveData.LevelProgressSaveData entry in progress)
			{
				if (entry == null || entry.BestScore <= 0)
				{
					continue;
				}
				try
				{
					CLevelManager.LevelData.Level level = CSettings.LevelTable[entry.LevelName];
					if (level != null)
					{
						await SubmitScoreAsync(BoardForLevel(level.ID), entry.BestScore);
					}
				}
				catch
				{
				}
				if (!string.IsNullOrEmpty(entry.Chapter))
				{
					chaptersSeen.Add(entry.Chapter);
				}
			}
			foreach (string chapterName in chaptersSeen)
			{
				try
				{
					CChapterScores chapter = scores.GetChapter(chapterName, assertIfMissing: false);
					if (chapter == null)
					{
						continue;
					}
					int total = chapter.GetScore();
					if (total <= 0)
					{
						continue;
					}
					int chapterId = ChapterIdForName(chapterName, progress);
					if (chapterId > 0)
					{
						await SubmitScoreAsync(BoardForChapter(chapterId), total);
					}
				}
				catch
				{
				}
			}
			int overall = scores.GetOverallTotalScore();
			if (overall > 0)
			{
				await SubmitScoreAsync(BoardOverall, overall);
			}
		}
		catch
		{
		}
	}

	private static int ChapterIdForName(string chapterName, CGameSaveData.LevelProgressSaveData[] progress)
	{
		foreach (CGameSaveData.LevelProgressSaveData entry in progress)
		{
			if (entry != null && entry.Chapter == chapterName)
			{
				try
				{
					CLevelManager.LevelData.Level level = CSettings.LevelTable[entry.LevelName];
					if (level != null && level.Chapter != null)
					{
						return level.Chapter.ID;
					}
				}
				catch
				{
				}
			}
		}
		return 0;
	}

	// ---- score submit ----

	public static void SubmitScore(string board, int score, Action<bool> callback)
	{
		if (!Configured || !HasUsername)
		{
			callback?.Invoke(false);
			return;
		}
		Task.Run(async delegate
		{
			bool ok = await SubmitScoreAsync(board, score);
			callback?.Invoke(ok);
		});
	}

	private static async Task<bool> SubmitScoreAsync(string board, int score)
	{
		if (!HasUsername)
		{
			return false;
		}
		try
		{
			string json = JsonSerializer.Serialize(new
			{
				p_username = s_Username,
				p_secret = s_DeviceSecret,
				p_board = board,
				p_score = score
			});
			using (StringContent content = new StringContent(json, Encoding.UTF8, "application/json"))
			{
				using (HttpResponseMessage response = await s_Http.PostAsync(SupabaseUrl + "/rest/v1/rpc/submit_score", content))
				{
					if (!response.IsSuccessStatusCode)
					{
						return false;
					}
					string body = await response.Content.ReadAsStringAsync();
					using (JsonDocument doc = JsonDocument.Parse(body))
					{
						return doc.RootElement.ValueKind == JsonValueKind.True;
					}
				}
			}
		}
		catch
		{
			return false;
		}
	}

	// ---- board reads ----

	// Top N rows for a board, plus the caller's own entry when they have
	// a username and are not already in the top N. (null top = error.)
	public static void GetBoardWithOwnRank(string board, int limit, Action<List<CLeaderboardEntry>, CLeaderboardEntry> callback)
	{
		if (!Configured)
		{
			callback?.Invoke(LocalBoard(board, limit), LocalOwnRow(board));
			return;
		}
		Task.Run(async delegate
		{
			List<CLeaderboardEntry> top = await GetBoardAsync(board, limit);
			CLeaderboardEntry own = null;
			if (top != null && HasUsername)
			{
				bool inTop = top.Any(delegate (CLeaderboardEntry e)
				{
					return string.Equals(e.Tag, s_Username, StringComparison.OrdinalIgnoreCase);
				});
				if (!inTop)
				{
					own = await GetPlayerRankAsync(board);
				}
			}
			callback?.Invoke(top, own);
		});
	}

	private static async Task<List<CLeaderboardEntry>> GetBoardAsync(string board, int limit)
	{
		try
		{
			string json = JsonSerializer.Serialize(new
			{
				p_board = board,
				p_limit = limit
			});
			using (StringContent content = new StringContent(json, Encoding.UTF8, "application/json"))
			{
				using (HttpResponseMessage response = await s_Http.PostAsync(SupabaseUrl + "/rest/v1/rpc/get_leaderboard", content))
				{
					if (!response.IsSuccessStatusCode)
					{
						return null;
					}
					string body = await response.Content.ReadAsStringAsync();
					List<CLeaderboardEntry> entries = new List<CLeaderboardEntry>();
					using (JsonDocument doc = JsonDocument.Parse(body))
					{
						foreach (JsonElement row in doc.RootElement.EnumerateArray())
						{
							CLeaderboardEntry entry = new CLeaderboardEntry
							{
								Pos = row.GetProperty("rank").GetInt32(),
								Tag = row.GetProperty("username").GetString(),
								Score = row.GetProperty("score").GetInt32()
							};
							entries.Add(entry);
						}
					}
					return entries;
				}
			}
		}
		catch
		{
			return null;
		}
	}

	private static async Task<CLeaderboardEntry> GetPlayerRankAsync(string board)
	{
		if (!HasUsername)
		{
			return null;
		}
		try
		{
			string json = JsonSerializer.Serialize(new
			{
				p_board = board,
				p_username = s_Username
			});
			using (StringContent content = new StringContent(json, Encoding.UTF8, "application/json"))
			{
				using (HttpResponseMessage response = await s_Http.PostAsync(SupabaseUrl + "/rest/v1/rpc/get_player_rank", content))
				{
					if (!response.IsSuccessStatusCode)
					{
						return null;
					}
					string body = await response.Content.ReadAsStringAsync();
					using (JsonDocument doc = JsonDocument.Parse(body))
					{
						foreach (JsonElement row in doc.RootElement.EnumerateArray())
						{
							return new CLeaderboardEntry
							{
								Pos = row.GetProperty("rank").GetInt32(),
								Tag = row.GetProperty("username").GetString(),
								Score = row.GetProperty("score").GetInt32()
							};
						}
					}
					return null;
				}
			}
		}
		catch
		{
			return null;
		}
	}

	// ---- level-end: submit the three boards, then read the level board ----

	// Submits level best + chapter total + overall total (only when the
	// player has a username), then reads the level's top 3 + own rank so
	// the fresh best is included. The read is anonymous when no username
	// is set, so the global board still shows.
	public static void SubmitLevelEndScores(int levelId, int chapterId, int levelBest, int chapterTotal, int overallTotal, Action<List<CLeaderboardEntry>, CLeaderboardEntry> onBoardReady)
	{
		if (!Configured)
		{
			onBoardReady?.Invoke(LocalBoard(BoardForLevel(levelId), 3), null);
			return;
		}
		Task.Run(async delegate
		{
			if (HasUsername)
			{
				await SubmitScoreAsync(BoardForLevel(levelId), levelBest);
				await SubmitScoreAsync(BoardForChapter(chapterId), chapterTotal);
				await SubmitScoreAsync(BoardOverall, overallTotal);
			}
			List<CLeaderboardEntry> top = await GetBoardAsync(BoardForLevel(levelId), 3);
			CLeaderboardEntry own = null;
			if (top != null && HasUsername)
			{
				bool inTop = top.Any(delegate (CLeaderboardEntry e)
				{
					return string.Equals(e.Tag, s_Username, StringComparison.OrdinalIgnoreCase);
				});
				if (!inTop)
				{
					own = await GetPlayerRankAsync(BoardForLevel(levelId));
				}
			}
			onBoardReady?.Invoke(top, own);
		});
	}
	// ---- local fallback (no backend configured) ----

	// Serves a board from the player's own save via LocalLeaderboards,
	// using the same board-id mapping the local backend uses: the menu
	// boards are overall + chapters 1..3, level boards are per level.
	private static List<CLeaderboardEntry> LocalBoard(string board, int limit)
	{
		if (board == BoardOverall)
		{
			return LocalLeaderboards.Read(0, false, limit);
		}
		if (board != null && board.StartsWith("chapter"))
		{
			int chapterId;
			if (int.TryParse(board.Substring("chapter".Length), out chapterId))
			{
				return LocalLeaderboards.Read(chapterId, false, limit);
			}
		}
		if (board != null && board.StartsWith("level:"))
		{
			int levelId;
			if (int.TryParse(board.Substring("level:".Length), out levelId))
			{
				return LocalLeaderboards.Read(levelId, false, limit);
			}
		}
		return new List<CLeaderboardEntry>();
	}

	// The player's own aggregate row for a menu board (null for level
	// boards - the level row itself is already in the board list).
	private static CLeaderboardEntry LocalOwnRow(string board)
	{
		int boardId = -1;
		if (board == BoardOverall)
		{
			boardId = 0;
		}
		else if (board != null && board.StartsWith("chapter"))
		{
			int chapterId;
			if (int.TryParse(board.Substring("chapter".Length), out chapterId))
			{
				boardId = chapterId;
			}
		}
		if (boardId < 0)
		{
			return null;
		}
		List<CLeaderboardEntry> pivot = LocalLeaderboards.Read(boardId, true, 1);
		return pivot.Count > 0 ? pivot[0] : null;
	}
}
