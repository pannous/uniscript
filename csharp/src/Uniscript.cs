// Uniscript for .NET: ASCII names for Unicode text (<:alpha> → α, <:fracture A> → 𝔄) and back, over the Rust crate's C ABI
using System.Text;

namespace Pannous;

/// <summary>Whether unsupported characters are warnings or errors; Lenient also turns errors (unknown entities, invalid
/// meta values, an unclosed &lt;:) into warnings and keeps their uniscript as written.</summary>
public enum UniscriptMode { Warn, Error, Lenient }

public enum UniscriptErrorKind { UnknownEntity = 1, Unclosed, Unsupported, InvalidMeta, InvalidInput }

/// <summary>A character or combination without a Unicode counterpart; At is a UTF-8 byte offset.</summary>
public readonly record struct UniscriptWarning(string Message, int At);

/// <summary>Message: that of the Rust error; Detail: the entity name, the rest after &lt;:, the warning message or the
/// tag; At: the offset of an Unsupported warning.</summary>
public sealed class UniscriptException(UniscriptErrorKind kind, string message, string detail, int at) : Exception(message)
{
	public UniscriptErrorKind Kind { get; } = kind;
	public string Detail { get; } = detail;
	public int At { get; } = at;
}

public sealed record Conversion(string Text, IReadOnlyList<UniscriptWarning> Warnings);

/// <summary>Version: "" when the header names none; Length: UTF-8 bytes of the header and the line break after it.</summary>
public sealed record UniscriptHeader(string Version, int Length);

/// <summary>A UTF-8 byte range [Start, End) of the plain text under one meta key; At: offset of its sequence in the tagged text.</summary>
public sealed record MetaRun(string Key, string Value, int Start, int End, int At);

/// <summary>Plain text without its meta sequences, the runs they cover (nested, in opening order) and the warnings.</summary>
public sealed record Styled(string Text, IReadOnlyList<MetaRun> Runs, IReadOnlyList<UniscriptWarning> Warnings);

/// <summary>A font style of the entities: the value of &lt;:font cuneiform-hittite&gt;; Lang in BCP 47.</summary>
public sealed record UniscriptFont(string Name, string Lang, IReadOnlyList<string> Families, IReadOnlyList<string> Features);

public static unsafe class Uniscript
{
	/// <summary>The uniscript version of the header &lt;:uniscript version="…"&gt;.</summary>
	public const string Version = "https://uniscript.org/v1";

	/// <summary>Uniscript → Unicode (meta information as TAG sequences) and its warnings; in Error mode the first
	/// warning is thrown.</summary>
	/// <exception cref="UniscriptException"/>
	public static Conversion Convert(string source, UniscriptMode mode = UniscriptMode.Warn) =>
		WithUtf8(source, text => Unwrap(Native.uniscript_convert(text, mode)));

	/// <summary>Uniscript → Unicode; warnings go to stderr.</summary>
	/// <exception cref="UniscriptException"/>
	public static string ToUnicode(string source)
	{
		Conversion conversion = Convert(source);
		foreach (UniscriptWarning warning in conversion.Warnings)
			Console.Error.WriteLine($"warning: uniscript: {warning.Message} at byte {warning.At}");
		return conversion.Text;
	}

	/// <summary>Unicode → uniscript; ToUnicode gives the text back.</summary>
	public static string ToUniscript(string text) => WithUtf8(text, utf8 => Take(Native.uniscript_to_uniscript(utf8)))
		?? throw new UniscriptException(UniscriptErrorKind.InvalidInput, "uniscript: invalid input (not UTF-8)", "", 0);

	/// <summary>The header &lt;:uniscript version="…"&gt; at the very start of the source, else null.</summary>
	public static UniscriptHeader? Header(string source) => WithUtf8(source, text =>
	{
		byte* version;
		nuint versionLength, length;
		if (Native.uniscript_header(text, &version, &versionLength, &length) == 0) return null;
		return new UniscriptHeader(Encoding.UTF8.GetString(version, (int)versionLength), (int)length);
	});

	/// <summary>Tagged text → plain text, nested meta runs and warnings (unknown keys, unmatched closes).</summary>
	public static Styled MetaRuns(string tagged) => WithUtf8(tagged, text =>
	{
		Native.Styled styled = Native.uniscript_meta_runs(text);
		try
		{
			var runs = List(styled.Runs, styled.RunCount, run =>
				new MetaRun(Read(run->Key), Read(run->Value), (int)run->Start, (int)run->End, (int)run->At));
			return new Styled(Read(styled.Text), runs, Warnings(styled.Warnings, styled.WarningCount));
		}
		finally { Native.uniscript_styled_free(&styled); }
	});

	/// <summary>HTML of tagged text (each meta run a &lt;span&gt; with its lang and CSS) and the warnings of MetaRuns.</summary>
	public static Conversion Html(string tagged) => WithUtf8(tagged, text => Unwrap(Native.uniscript_html(text)));

	/// <summary>A font style of the entities (cuneiform-hittite, han-japanese), else null.</summary>
	public static UniscriptFont? Font(string name) => WithUtf8(name, text =>
	{
		Native.Font font;
		if (Native.uniscript_font_lookup(text, &font) == 0) return null;
		try
		{
			return new UniscriptFont(Read(font.Name), Read(font.Lang),
				Strings(font.Families, font.FamilyCount), Strings(font.Features, font.FeatureCount));
		}
		finally { Native.uniscript_font_free(&font); }
	});

	/// <summary>The CSS declaration template of a meta key (color → "color: {}"), else null.</summary>
	public static string? MetaTemplate(string key) => WithUtf8(key, text => Take(Native.uniscript_meta_template(text)));

	private delegate T Utf8Call<T>(byte* text);
	private delegate T Element<TNative, T>(TNative* element) where TNative : unmanaged;

	private static T WithUtf8<T>(string text, Utf8Call<T> call)
	{
		ArgumentNullException.ThrowIfNull(text);
		if (text.Contains('\0')) throw new ArgumentException("uniscript text cannot hold U+0000: the C ABI reads NUL-terminated strings", nameof(text));
		byte[] utf8 = new byte[Encoding.UTF8.GetByteCount(text) + 1];
		Encoding.UTF8.GetBytes(text, utf8);
		fixed (byte* pointer = utf8) return call(pointer);
	}

	private static string Read(byte* text) => text == null ? "" : new string((sbyte*)text, 0, Length(text), Encoding.UTF8);

	private static int Length(byte* text)
	{
		int length = 0;
		while (text[length] != 0) length++;
		return length;
	}

	private static string? Take(byte* text)
	{
		if (text == null) return null;
		try { return Read(text); }
		finally { Native.uniscript_free(text); }
	}

	private static T[] List<TNative, T>(TNative* items, nuint count, Element<TNative, T> convert) where TNative : unmanaged
	{
		var list = new T[(int)count];
		for (int i = 0; i < list.Length; i++) list[i] = convert(items + i);
		return list;
	}

	private static string[] Strings(byte** items, nuint count)
	{
		var strings = new string[(int)count];
		for (int i = 0; i < strings.Length; i++) strings[i] = Read(items[i]);
		return strings;
	}

	private static UniscriptWarning[] Warnings(Native.Warning* warnings, nuint count) =>
		List(warnings, count, warning => new UniscriptWarning(Read(warning->Message), (int)warning->At));

	private static Conversion Unwrap(Native.Result result)
	{
		try
		{
			if (result.ErrorKind != Native.ErrorKind.Ok)
				throw new UniscriptException((UniscriptErrorKind)result.ErrorKind, Read(result.Error), Read(result.ErrorDetail), (int)result.ErrorAt);
			return new Conversion(Read(result.Text), Warnings(result.Warnings, result.WarningCount));
		}
		finally { Native.uniscript_result_free(&result); }
	}
}
