using Microsoft.Xna.Framework.Content;

namespace FableCoinGolfCompat
{
    /// <summary>
    /// Phase 3 compat reader: XNA content with object-typed reflective members
    /// (e.g. CustomModelPart.Tag) stores values polymorphically — a 7-bit reader
    /// index followed by the value written by that reader. MonoGame's
    /// ReflectiveReader throws at Initialize because no reader targets
    /// System.Object. This reader is appended to the reader table of every
    /// packaged XNB (build copies only) so GetTypeReader(typeof(object))
    /// succeeds; the actual member read still goes through ContentReader's
    /// index-based polymorphic path, exactly as XNA did.
    /// Derives from the non-generic ContentTypeReader because
    /// ContentTypeReader&lt;object&gt; has colliding Read signatures (CS0462).
    /// </summary>
    public class ObjectFallbackReader : ContentTypeReader
    {
        public ObjectFallbackReader() : base(typeof(object))
        {
        }

        protected override object Read(ContentReader input, object existingInstance)
        {
            return input.ReadObject<object>(existingInstance);
        }
    }
}
