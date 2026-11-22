using Microsoft.Xna.Framework;

// TRACK-C WS3 (temporary-support, keep with the feature): render-time
// interpolation state for the player puck. The scaffold Game snapshots the
// puck ent's world translation after each fixed 30 Hz engine quantum and
// publishes (Prev, Cur, Alpha) here; CIwRenderableModel.SetupGraphicsState
// offsets the player puck's model matrix by (Prev-Cur)*(1-Alpha), which
// renders the puck one logic step behind real time, gliding between states.
// All other rendering (camera included) already damps by wall-clock in the
// engine's render path (CIwCamera.SelectForRender), so it smooths itself
// at the higher presentation rate.
public static class FcgInterp
{
	public static bool Valid;
	public static Vector3 Prev;
	public static Vector3 Cur;
	public static float Alpha;

	public static void Set(Vector3 prev, Vector3 cur, float alpha)
	{
		Prev = prev;
		Cur = cur;
		Alpha = alpha;
		Valid = true;
	}

	public static void ApplyToOwner(CIwEnt owner, CIwXnaRenderState renderState)
	{
		if (!Valid || owner == null || renderState == null)
		{
			return;
		}
		try
		{
			CIwEnt ent = owner;
			CIwPuck found = null;
			CIwFrame frame = null;
			while (ent != null)
			{
				CIwPuck puck = ent.GetComponent<CIwPuck>(11);
				if (puck != null)
				{
					found = puck;
					frame = ent.GetComponent<CIwFrame>(0);
					break;
				}
				ent = ent.GetParent();
			}
			if (found == null || frame == null)
			{
				return;
			}
			if (found != CPuckManager.Instance.PlayerPuck)
			{
				return;
			}
			Vector3 offset = (Prev - Cur) * (1f - Alpha);
			if (offset.LengthSquared() < 1e-10f)
			{
				return;
			}
			Matrix m = renderState.ModelMatrix;
			m.Translation += offset;
			renderState.ModelMatrix = m;
		}
		catch
		{
		}
	}
}
