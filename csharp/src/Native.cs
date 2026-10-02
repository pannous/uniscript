// The C ABI of c/uniscript.h: every string NUL-terminated UTF-8, returned ones owned by the library
using System.Runtime.InteropServices;

namespace Pannous;

internal static unsafe partial class Native
{
	private const string Library = "uniscript";

	internal enum ErrorKind { Ok, UnknownEntity, Unclosed, Unsupported, InvalidMeta, InvalidInput }

	[StructLayout(LayoutKind.Sequential)]
	internal struct Warning
	{
		public byte* Message;
		public nuint At;
	}

	[StructLayout(LayoutKind.Sequential)]
	internal struct Result
	{
		public byte* Text;
		public ErrorKind ErrorKind;
		public byte* Error;
		public byte* ErrorDetail;
		public nuint ErrorAt;
		public Warning* Warnings;
		public nuint WarningCount;
	}

	[StructLayout(LayoutKind.Sequential)]
	internal struct MetaRun
	{
		public byte* Key;
		public byte* Value;
		public nuint Start, End, At;
	}

	[StructLayout(LayoutKind.Sequential)]
	internal struct Styled
	{
		public byte* Text;
		public MetaRun* Runs;
		public nuint RunCount;
		public Warning* Warnings;
		public nuint WarningCount;
	}

	[StructLayout(LayoutKind.Sequential)]
	internal struct Font
	{
		public byte* Name;
		public byte* Lang;
		public byte** Families;
		public nuint FamilyCount;
		public byte** Features;
		public nuint FeatureCount;
	}

	[LibraryImport(Library)] internal static partial Result uniscript_convert(byte* source, UniscriptMode mode);
	[LibraryImport(Library)] internal static partial byte* uniscript_to_uniscript(byte* text);
	[LibraryImport(Library)] internal static partial byte* uniscript_explicit(byte* source);
	[LibraryImport(Library)] internal static partial int uniscript_header(byte* source, byte** version, nuint* versionLength, nuint* length);
	[LibraryImport(Library)] internal static partial Styled uniscript_meta_runs(byte* tagged);
	[LibraryImport(Library)] internal static partial Result uniscript_html(byte* tagged);
	[LibraryImport(Library)] internal static partial int uniscript_font_lookup(byte* name, Font* font);
	[LibraryImport(Library)] internal static partial byte* uniscript_meta_template(byte* key);
	[LibraryImport(Library)] internal static partial void uniscript_free(byte* text);
	[LibraryImport(Library)] internal static partial void uniscript_result_free(Result* result);
	[LibraryImport(Library)] internal static partial void uniscript_styled_free(Styled* styled);
	[LibraryImport(Library)] internal static partial void uniscript_font_free(Font* font);
}
