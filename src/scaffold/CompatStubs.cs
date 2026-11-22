// Small BCL-surface compat shims: members the WP7/Silverlight profile had
// that the net8.0-android reference pack does not expose the same way.
namespace System.Diagnostics
{
    public static class StopwatchCompatExtensions
    {
        // WP7 Stopwatch.GetRawElapsedTicks() — raw timer ticks without frequency scaling.
        // ElapsedTicks is the closest portable equivalent for the profiler's use.
        public static long GetRawElapsedTicks(this Stopwatch stopwatch) => stopwatch.ElapsedTicks;
    }
}
