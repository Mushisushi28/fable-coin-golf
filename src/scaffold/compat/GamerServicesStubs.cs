// Minimal Microsoft.Xna.Framework.GamerServices + Microsoft.Phone.Tasks stubs.
// MonoGame.Framework.Android 3.8.2.1105 ships NO GamerServices namespace (verified by
// build2 CS0234/CS0246 errors), so the offline port provides its own: Xbox Live is dead,
// Guide.IsTrialMode is permanently false (full game), sign-in never happens.
using System;
using Microsoft.Xna.Framework;

namespace Microsoft.Xna.Framework.GamerServices
{
    public enum LeaderboardKey
    {
        BestScoreLifeTime = 0
    }

    public class Gamer
    {
        public string Gamertag { get; set; } = "";
    }

    public class SignedInGamer : Gamer
    {
        // ACH/LB local backend: the only gamer is the local profile, which
        // is always "signed in" locally (ACH-LB-PLAN.md §1.4.1) so direct
        // property checks agree with CIwXBOXLiveWrapper.IsSignedIntoLive.
        public bool IsSignedInToLive => true;
        public PlayerIndex PlayerIndex => PlayerIndex.One;
    }

    public class SignedInEventArgs : EventArgs
    {
        public SignedInGamer Gamer { get; set; }
    }

    public static class Guide
    {
        public static bool IsTrialMode => false;
        public static bool SimulateTrialMode { get; set; }
        public static void ShowMarketplace(PlayerIndex playerIndex) { }
    }

    public class GamerServicesComponent : GameComponent
    {
        public GamerServicesComponent(Game game) : base(game) { }
    }

    // XNA GamerServices exception types the game catches around Live calls.
    // Never thrown by the offline stubs; present so the catch blocks compile.
    public class GameUpdateRequiredException : Exception
    {
        public GameUpdateRequiredException() { }
        public GameUpdateRequiredException(string message) : base(message) { }
    }

    public class GamerServicesNotAvailableException : Exception
    {
        public GamerServicesNotAvailableException() { }
        public GamerServicesNotAvailableException(string message) : base(message) { }
    }
}

namespace Microsoft.Phone.Tasks
{
    public enum MarketplaceContentType
    {
        Applications = 0,
        Music = 1
    }

    // Used by CIwUiPageManager for the WP7 marketplace upsell page; no-op on Android.
    public class MarketplaceDetailTask
    {
        public string ContentIdentifier { get; set; }
        public MarketplaceContentType ContentType { get; set; }
        public void Show() { }
    }
}
