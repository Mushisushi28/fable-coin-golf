// Local-backend replacement for XBOXLiveConnectivity.dll's CIwXBOXLiveWrapper.
// STAGED 2026-11-14 (implementation prep per ACH-LB-PLAN.md §§1.4/2.2). NOT
// yet in srcC: replaces FableCoinGolf.Android\XboxLiveStub.cs when the ACH/LB
// implementation phase starts. All public signatures are unchanged from the
// current stub (which copied them 1:1 from the decompiled original).
//
// Xbox Live for WP7 is dead. Instead of the old no-op stub — whose
// SignInGamer accepted the callback and NEVER invoked it, parking both
// leaderboard surfaces on "SYNCING…" forever (plan §0) — this backend
// completes every operation synchronously against local data:
//   - one process-wide local gamer ("YOU", see LocalLeaderboards);
//   - achievements read as snapshot copies of the save's own
//     SavedAchievements (never null — plan §1.3 hazard A) and committed to
//     disk on earn via the game's own DoSaveAll (plan §1.4.3);
//   - leaderboard reads synthesized from the player's own GameScores by
//     LocalLeaderboards; writes are accept-and-report-success (they exactly
//     mirror GameScores state the game persists itself, plan §2.2).
// CAchievement and CLeaderboardEntry are NOT stubbed here — the original
// decompiled POCO sources are compiled in directly (see csproj).
using System;
using System.Collections.Generic;
using Microsoft.Xna.Framework.GamerServices;

public static class CIwXBOXLiveWrapper
{
    public delegate void ReadLeaderboardHandler(IEnumerable<CLeaderboardEntry> entries);
    public delegate void WriteLeaderboardHandler(bool success);
    public delegate void ReadAchievementsHandler(IEnumerable<CAchievement> achievements);
    public delegate void WriteAchievementHandler(bool success);
    public delegate void DebugTraceFn(int channel, string msg);
    public delegate void DebugAssertFn(bool con, string msg);
    public delegate void HandleGameUpdateFn();

    public static bool m_Disabled = false;
    public static DebugTraceFn DebugTrace;
    public static DebugAssertFn DebugAssert;
    public static HandleGameUpdateFn HandleGameUpdate = null;
    public static bool TUExceptionBuild = false;
    public static int DebugTraceChannel { get; set; }

    // The single local profile. Process-wide so every consumer sees the
    // same identity object (own-entry detection compares tags, and the
    // frontend sync compares achievement snapshots, never references).
    private static readonly SignedInGamer LocalGamer = new SignedInGamer { Gamertag = LocalLeaderboards.LocalPlayerName };

    // Any gamer this backend hands out IS the local profile (plan §1.4.1).
    public static bool IsSignedIntoLive(SignedInGamer gamer) => gamer != null;
    public static SignedInGamer GetSignedInGamer() => LocalGamer;
    public static string GetGamerTag(Gamer gamer) => gamer != null ? gamer.Gamertag : "";

    // No-op for the local backend (plan §1.4.1): DisableService is only
    // called on a GameUpdateRequiredException our stubs never throw, and a
    // Live kill-switch must not be able to re-break local features. The
    // m_Disabled field is kept for signature compatibility and ignored.
    public static void DisableService() { }

    // THE fix for both SYNCING hangs: the callback fires synchronously, in
    // this call stack, with the local gamer. All three consumers
    // (frontend, leaderboards menu, level end) use only args.Gamer —
    // sender is never read (verified in the decompiled sources).
    public static void SignInGamer(EventHandler<SignedInEventArgs> GamerSignedInCallback)
    {
        GamerSignedInCallback?.Invoke(null, new SignedInEventArgs { Gamer = LocalGamer });
    }

    // Callbacks are one-shot under the local backend; nothing to unregister.
    public static void UnregisterSignInGamerCallback(EventHandler<SignedInEventArgs> GamerSignedInCallback) { }

    public static void ReadLeaderboard(LeaderboardKey leaderboard, int variationId, ReadLeaderboardHandler handler, bool pivotGamer, int count)
    {
        // LocalLeaderboards.Read never returns null and never throws.
        handler?.Invoke(LocalLeaderboards.Read(variationId, pivotGamer, count));
    }

    public static void WriteLeaderboard(LeaderboardKey leaderboard, int variationId, int score, WriteLeaderboardHandler handler)
    {
        // Accept-and-report-success (plan §2.2): the three level-end writes
        // exactly mirror GameScores state, reads derive from GameScores,
        // and the caller's own DoSaveGameProgress() persists that state in
        // the same PopulateContainer. A second store would only add a
        // divergence risk.
        handler?.Invoke(true);
    }

    public static void ReadAchievements(ReadAchievementsHandler handler)
    {
        // Fresh snapshot copies of the save's own achievements, in enum
        // order, NEVER null (plan §1.3 hazard A: SyncAchievements
        // dereferences the result outside its null guard whenever any
        // local earn exists). Copies, not aliases: Sync is union-only and
        // reference-inequality just makes it re-commit earns through
        // WriteAchievement, which is an idempotent local commit (hazard B).
        List<CAchievement> snapshot = new List<CAchievement>();
        try
        {
            CAchievement[] saved = CSaveManager.Instance.gameSaveData.SavedAchievements;
            foreach (CAchievement entry in saved)
            {
                snapshot.Add(new CAchievement(entry.Key) { IsEarned = entry.IsEarned });
            }
        }
        catch
        {
            // Save not loaded yet: synthesize the 11 unearned entries the
            // same way CGameSaveData's constructor does, so the handler
            // still receives a well-formed, non-null list.
            snapshot.Clear();
            for (int i = 0; i < (int)CSettings.AchievementKeys.Max; i++)
            {
                snapshot.Add(new CAchievement(((CSettings.AchievementKeys)i).ToString().ToLower()));
            }
        }
        handler?.Invoke(snapshot);
    }

    public static void WriteAchievement(string achievementKey, WriteAchievementHandler handler)
    {
        // Commit-on-earn (plan §1.4.3): SaveAchievement has already set
        // IsEarned in the live save object before calling here; serialize
        // the whole save now so every earn is durable the moment it fires
        // (closes the mid-level persistence gap, plan §1.3). DoSaveAll is
        // the game's own save path — same serializer, same file.
        try
        {
            CSaveManager.Instance.DoSaveAll(false);
        }
        catch
        {
            // A failed commit must not break the earn flow; the flag is
            // set in memory and the next regular save point persists it,
            // exactly as the game behaved on WP7.
        }
        handler?.Invoke(true);
    }

    public static void SetGameUpdateFn(HandleGameUpdateFn fn) { HandleGameUpdate = fn; }
}
