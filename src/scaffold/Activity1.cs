using System;
using Android.App;
using Android.Content;
using Android.Content.PM;
using Android.Graphics;
using Android.OS;
using Android.Views;
using Android.Views.InputMethods;
using Android.Widget;
using Microsoft.Xna.Framework;
using Tech.localisation;

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
        public static Activity1 Instance { get; private set; }

        private Game _game;

        // Username dialog state. The dialog is styled to the game's design
        // language (parchment panel, gold flourishes, Cinzel text — the
        // closest available match for the game's Charlemagne font; see
        // Assets/fonts/cinzel.ttf, SIL OFL 1.1, licence in OFL.txt).
        // The dialog stays open while the username claim is checked and
        // only closes on success; "taken" / network errors are shown
        // inside it. NOTE: the Android system keyboard that appears for
        // the EditText is stock and cannot be themed to the game.
        private AlertDialog _usernameDialog;
        private EditText _usernameInput;
        private TextView _usernameStatus;
        private Button _usernameSaveButton;
        private bool _usernameDialogCompleted;

        protected override void OnCreate(Bundle bundle)
        {
            base.OnCreate(bundle);
            Instance = this;
            _game = new Game();
            SetContentView((View)_game.Services.GetService(typeof(View)));
            // TRACK-C WS3: ask the display for its highest refresh rate (Pixel 8 Pro
            // panel is 120 Hz) so the scaffold's decoupled Draw can present at
            // 120 Hz while engine logic stays at its tuned 30 Hz.
            try
            {
                var attrs = Window.Attributes;
                attrs.PreferredRefreshRate = 120f;
                Window.Attributes = attrs;
            }
            catch
            {
            }
            _game.Run();
        }

        // Called from the game thread (Settings menu). Marshals to the UI
        // thread, shows the dialog, and returns immediately. onSubmit is
        // invoked on the UI thread when the player taps Save with a
        // locally-valid name; the dialog stays open until
        // FinishUsernameDialog reports the claim result.
        public void ShowUsernameDialog(string currentUsername, Action<string> onSubmit, Action onCancel)
        {
            RunOnUiThread(() =>
            {
                try
                {
                    ShowUsernameDialogOnUiThread(currentUsername, onSubmit, onCancel);
                }
                catch
                {
                    // A dialog failure must never break the game; the
                    // player simply stays without a username.
                    onCancel?.Invoke();
                }
            });
        }

        private void ShowUsernameDialogOnUiThread(string currentUsername, Action<string> onSubmit, Action onCancel)
        {
            _usernameDialogCompleted = false;
            LayoutInflater inflater = LayoutInflater.From(this);
            View view = inflater.Inflate(Resource.Layout.dialog_username, null);

            Typeface gameFont = LoadGameFont();
            TextView title = view.FindViewById<TextView>(Resource.Id.username_title);
            TextView message = view.FindViewById<TextView>(Resource.Id.username_message);
            _usernameInput = view.FindViewById<EditText>(Resource.Id.username_input);
            _usernameStatus = view.FindViewById<TextView>(Resource.Id.username_status);
            _usernameSaveButton = view.FindViewById<Button>(Resource.Id.username_save);
            Button cancelButton = view.FindViewById<Button>(Resource.Id.username_cancel);

            title.Text = fabmob.USERNAME_DIALOG_TITLE;
            message.Text = fabmob.USERNAME_DIALOG_MESSAGE;
            _usernameInput.Hint = fabmob.USERNAME_DIALOG_HINT;
            _usernameSaveButton.Text = fabmob.USERNAME_DIALOG_SAVE;
            cancelButton.Text = fabmob.USERNAME_DIALOG_CANCEL;
            if (gameFont != null)
            {
                title.Typeface = gameFont;
                message.Typeface = gameFont;
                _usernameInput.Typeface = gameFont;
                _usernameStatus.Typeface = gameFont;
                _usernameSaveButton.Typeface = gameFont;
                cancelButton.Typeface = gameFont;
            }
            if (!string.IsNullOrEmpty(currentUsername))
            {
                _usernameInput.Text = currentUsername;
                _usernameInput.SetSelection(_usernameInput.Text.Length);
            }
            _usernameStatus.Visibility = ViewStates.Gone;

            _usernameSaveButton.Click += (sender, e) =>
            {
                string name = _usernameInput.Text ?? "";
                if (CLeaderboardService.ValidateUsername(name) == null)
                {
                    ShowUsernameStatus(fabmob.USERNAME_INVALID);
                    return;
                }
                ShowUsernameStatus(fabmob.USERNAME_CHECKING);
                _usernameSaveButton.Enabled = false;
                try
                {
                    onSubmit?.Invoke(name.Trim());
                }
                catch
                {
                    _usernameSaveButton.Enabled = true;
                    ShowUsernameStatus(fabmob.USERNAME_NO_CONNECTION);
                }
            };
            cancelButton.Click += (sender, e) =>
            {
                _usernameDialogCompleted = true;
                _usernameDialog?.Dismiss();
                onCancel?.Invoke();
            };

            AlertDialog.Builder builder = new AlertDialog.Builder(this, Resource.Style.UsernameDialogTheme);
            builder.SetView(view);
            builder.SetCancelable(true);
            _usernameDialog = builder.Create();
            _usernameDialog.DismissEvent += (sender, e) =>
            {
                if (!_usernameDialogCompleted)
                {
                    _usernameDialogCompleted = true;
                    onCancel?.Invoke();
                }
            };
            _usernameDialog.Show();
            _usernameInput.RequestFocus();
            try
            {
                InputMethodManager imm = (InputMethodManager)GetSystemService(InputMethodService);
                imm?.ShowSoftInput(_usernameInput, ShowFlags.Implicit);
            }
            catch
            {
            }
        }

        // Called (on any thread) with the claim result. Safe to call from
        // the service's background-thread callback: marshals to the UI
        // thread. Success dismisses the dialog; anything else shows the
        // error inside it and re-enables Save.
        public void FinishUsernameDialog(CLeaderboardService.ClaimResult result)
        {
            RunOnUiThread(() =>
            {
                try
                {
                    if (_usernameDialog == null || _usernameDialogCompleted)
                    {
                        return;
                    }
                    switch (result)
                    {
                        case CLeaderboardService.ClaimResult.Success:
                            _usernameDialogCompleted = true;
                            _usernameDialog.Dismiss();
                            break;
                        case CLeaderboardService.ClaimResult.Taken:
                            ShowUsernameStatus(fabmob.USERNAME_TAKEN);
                            if (_usernameSaveButton != null)
                            {
                                _usernameSaveButton.Enabled = true;
                            }
                            break;
                        case CLeaderboardService.ClaimResult.Invalid:
                            ShowUsernameStatus(fabmob.USERNAME_INVALID);
                            if (_usernameSaveButton != null)
                            {
                                _usernameSaveButton.Enabled = true;
                            }
                            break;
                        default:
                            ShowUsernameStatus(fabmob.USERNAME_NO_CONNECTION);
                            if (_usernameSaveButton != null)
                            {
                                _usernameSaveButton.Enabled = true;
                            }
                            break;
                    }
                }
                catch
                {
                }
            });
        }

        private void ShowUsernameStatus(string text)
        {
            if (_usernameStatus == null)
            {
                return;
            }
            _usernameStatus.Text = text;
            _usernameStatus.Visibility = ViewStates.Visible;
        }

        // Cinzel (SIL OFL 1.1) from Assets/fonts — loaded from assets so
        // it works on every API level the game supports (font resources
        // need API 26+ in XML). Falls back to the default typeface.
        private Typeface LoadGameFont()
        {
            try
            {
                return Typeface.CreateFromAsset(Assets, "fonts/cinzel.ttf");
            }
            catch
            {
                return null;
            }
        }
    }
}
