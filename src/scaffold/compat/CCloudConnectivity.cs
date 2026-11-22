// Local no-network replacement for the decompiled CCloudConnectivity.
// STAGED 2026-11-14 (implementation prep per ACH-LB-PLAN.md §1.4.4). NOT yet
// in srcC: drops into FableCoinGolf.Android\ when the ACH/LB phase starts,
// with the csproj Tech glob excluding the decompiled original (same pattern
// as CIwRenderableModel.cs etc.).
//
// The original POSTs SOAP to the dead Lionhead service
// (regislidecert.lionhead-int.com) for Fable III gold/item transfers and
// fetches avatar images over HTTP. Every public member keeps its exact
// signature; every operation completes synchronously with the local
// success semantics the plan specifies. No request is ever constructed.
using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Xna.Framework.GamerServices;
using Microsoft.Xna.Framework.Graphics;

public static class CCloudConnectivity
{
	public delegate void Callback(bool success, int id);

	public delegate void CallbackImage(Texture2D texture);

	public delegate void HandleGameUpdateFn();

	public static HandleGameUpdateFn HandleGameUpdate = null;

	// Console vars kept from the original so any config/console reader sees
	// the same registrations. Inert: nothing in this backend reads them.
	private static CIwConsole.Var<string> ConnectURL = CIwConsole.Inst.Register("CloudConnectURL", "");

	private static CIwConsole.Var<string> SoapURL = CIwConsole.Inst.Register("CloudSoapURL", "");

	private static CIwConsole.Var<string> AvatarURL = CIwConsole.Inst.Register("XBOXAvatarURL", "");

	private static Dictionary<string, Texture2D> m_CachedAvatars = new Dictionary<string, Texture2D>();

	// No-op (plan §1.4.4): a service kill-switch must not break local play.
	public static void DisableService()
	{
	}

	public static void SetGameUpdateFn(HandleGameUpdateFn fn)
	{
		HandleGameUpdate = fn;
	}

	// The sent_gold local completion (project decision: reinterpret the
	// dead Fable III transfer as banking gold at level end). CPlayerInfo.
	// SyncGold calls this once the wrapper reports a signed-in gamer; the
	// synchronous success callback zeroes UnsyncedGold and earns the
	// achievement through the game's own OnSyncGoldCallback path.
	public static void AwardGold(int amount, Callback callback)
	{
		callback?.Invoke(true, -1);
	}

	public static void TestGetGold(Callback callback)
	{
		callback?.Invoke(true, -1);
	}

	// Chapter-complete Fable III items cannot actually be granted (§5 of
	// the plan — the service is dead); reporting success retires the
	// RetryToAwardItem bookkeeping so chapter earns stop re-queueing.
	public static void AwardItem(string itemName, Callback callback, int id)
	{
		callback?.Invoke(true, id);
	}

	// Avatars: a cached texture is returned if one was ever added; otherwise
	// null, synchronously. Both UIs treat a null texture as "keep the
	// template image" and advance their avatar chains (plan §2.1).
	public static void GetAvatar(string gamertag, CallbackImage callback)
	{
		Texture2D cached;
		if (gamertag != null && m_CachedAvatars.TryGetValue(gamertag, out cached))
		{
			callback?.Invoke(cached);
			return;
		}
		callback?.Invoke(null);
	}

	public static void AddToCachedAvatars(string gamer, Texture2D avatar)
	{
		m_CachedAvatars[gamer] = avatar;
	}

	// Kept byte-compatible with the original for any internal caller.
	internal static string CalculateHash(string input)
	{
		HMACSHA256 hMACSHA = new HMACSHA256(Encoding.UTF8.GetBytes("osujdblkw4t8hsljblw48thsvljdb,j4sbtpi"));
		byte[] bytes = Encoding.UTF8.GetBytes(input);
		byte[] array = hMACSHA.ComputeHash(bytes);
		StringBuilder stringBuilder = new StringBuilder();
		for (int i = 0; i < array.Length; i++)
		{
			stringBuilder.Append(array[i].ToString("X2"));
		}
		return stringBuilder.ToString();
	}
}
