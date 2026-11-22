// Minimal WP7-only API stubs for the Phase 2 compile probe.
// Production port: PhoneApplicationService maps to Android lifecycle callbacks;
// Microsoft.Devices.Environment.DeviceType is a compile-time-only shim.
using System;
using System.Collections.Generic;

namespace Microsoft.Phone.Shell
{
    public class LaunchingEventArgs : EventArgs { }
    public class ActivatedEventArgs : EventArgs { public bool IsApplicationInstancePreserved { get; set; } }
    public class DeactivatedEventArgs : EventArgs { }
    public class ClosingEventArgs : EventArgs { }

    public class PhoneApplicationService
    {
        private static readonly PhoneApplicationService _current = new PhoneApplicationService();
        public static PhoneApplicationService Current => _current;

        public IDictionary<string, object> State { get; } = new Dictionary<string, object>();

        public event EventHandler<LaunchingEventArgs> Launching;
        public event EventHandler<ActivatedEventArgs> Activated;
        public event EventHandler<DeactivatedEventArgs> Deactivated;
        public event EventHandler<ClosingEventArgs> Closing;

        // Events are never raised in the probe; accessors referenced to silence CS0067.
        private void SuppressWarnings()
        {
            _ = Launching; _ = Activated; _ = Deactivated; _ = Closing;
        }
    }
}

namespace Microsoft.Devices
{
    public enum DeviceType
    {
        Unknown = 0,
        PhysicalDevice = 1,
        VirtualDevice = 2
    }

    public static class Environment
    {
        public static DeviceType DeviceType => DeviceType.PhysicalDevice;
    }
}
