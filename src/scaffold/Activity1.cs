using Android.App;
using Android.Content.PM;
using Android.OS;
using Android.Views;
using Microsoft.Xna.Framework;

namespace FableCoinGolf.Android
{
    [Activity(
        Label = "Fable Coin Golf",
        MainLauncher = true,
        Icon = "@mipmap/icon",
        Theme = "@android:style/Theme.NoTitleBar.Fullscreen",
        AlwaysRetainTaskState = true,
        LaunchMode = LaunchMode.SingleInstance,
        ScreenOrientation = ScreenOrientation.Portrait,
        ConfigurationChanges = ConfigChanges.Orientation | ConfigChanges.Keyboard | ConfigChanges.KeyboardHidden | ConfigChanges.ScreenSize)]
    public class Activity1 : AndroidGameActivity
    {
        private Game _game;

        protected override void OnCreate(Bundle bundle)
        {
            base.OnCreate(bundle);
            _game = new Game();
            SetContentView((View)_game.Services.GetService(typeof(View)));
            _game.Run();
        }
    }
}
