using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.Xna.Framework.Content;

namespace FableCoinGolfCompat
{
    /// <summary>
    /// Phase 3 compat: WP7/Windows content lookup is case-insensitive; Android's
    /// AssetManager is case-sensitive. The game's data was authored
    /// case-insensitively, so requests arrive in spellings that match neither
    /// the file's case nor all-lowercase (e.g. file "puckTrailWoodsman.xnb"
    /// requested as "PuckTrailWoodsman" via string concatenation). Duplicating
    /// files per spelling cannot close that class; resolving at load time can.
    /// Every game load funnels through the single ContentManager the scaffold
    /// hands to CIwXnaContentManager, so this subclass is installed as
    /// Game.Content: on a miss it retries with the real packaged path taken
    /// from a lazily built case-insensitive index of the APK's asset tree.
    /// </summary>
    public class CaseFixContentManager : ContentManager
    {
        private static Dictionary<string, string> s_AssetIndex;

        public CaseFixContentManager(IServiceProvider serviceProvider)
            : base(serviceProvider)
        {
        }

        protected override Stream OpenStream(string assetName)
        {
            try
            {
                return base.OpenStream(assetName);
            }
            catch (Exception)
            {
                string actualName;
                if (TryResolve(assetName, out actualName))
                {
                    return base.OpenStream(actualName);
                }
                throw;
            }
        }

        private bool TryResolve(string assetName, out string actualName)
        {
            actualName = null;
            EnsureIndex();
            if (s_AssetIndex == null)
            {
                return false;
            }
            string root = (RootDirectory ?? string.Empty).Replace('\\', '/').TrimEnd('/');
            string rel = assetName.Replace('\\', '/').TrimStart('/');
            string full = (root.Length > 0 ? root + "/" : string.Empty) + rel + ".xnb";
            string actual;
            if (!s_AssetIndex.TryGetValue(full.ToLowerInvariant(), out actual))
            {
                return false;
            }
            string prefix = root.Length > 0 ? root + "/" : string.Empty;
            string name = actual.StartsWith(prefix, StringComparison.Ordinal)
                ? actual.Substring(prefix.Length)
                : actual;
            if (name.EndsWith(".xnb", StringComparison.OrdinalIgnoreCase))
            {
                name = name.Substring(0, name.Length - 4);
            }
            actualName = name;
            return true;
        }

        private static void EnsureIndex()
        {
            if (s_AssetIndex != null)
            {
                return;
            }
            try
            {
                var map = new Dictionary<string, string>();
                var assets = Android.App.Application.Context.Assets;
                var pending = new Stack<string>();
                pending.Push("Content");
                while (pending.Count > 0)
                {
                    string dir = pending.Pop();
                    string[] entries = null;
                    try { entries = assets.List(dir); } catch { }
                    if (entries == null)
                    {
                        continue;
                    }
                    foreach (string entry in entries)
                    {
                        string path = dir + "/" + entry;
                        string[] children = null;
                        try { children = assets.List(path); } catch { }
                        if (children != null && children.Length > 0)
                        {
                            pending.Push(path);
                        }
                        else
                        {
                            map[path.ToLowerInvariant()] = path;
                        }
                    }
                }
                s_AssetIndex = map;
            }
            catch
            {
                s_AssetIndex = new Dictionary<string, string>();
            }
        }
    }
}
