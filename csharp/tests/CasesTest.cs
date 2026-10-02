// The shared cases of js/test/cases.json (ported from the Rust tests/*.rs) against the C# library
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Pannous;
using Xunit;

public class CasesTest
{
	private const int TagBase = 0xE0000;
	private const string CancelTag = "\U000E007F";
	private static readonly Regex Expansion = new(@"\{(U\+([0-9A-Fa-f]+)|open (\S+) (\S+)|close (\S+)|attached (\S+) (\S+))\}");
	private static readonly JsonElement Cases = JsonDocument.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "cases.json"))).RootElement;

	/// <summary>the meta TAG sequence of `&lt;key value`, `&lt;/key` or `:key value`</summary>
	private static string Tags(string spelled) =>
		string.Concat(spelled.Select(c => char.ConvertFromUtf32(TagBase + c))) + CancelTag;

	/// <summary>{U+E0072} → the code point, {open key value} {close key} {attached key value} → the meta TAG sequence</summary>
	private static string Expand(string text) => Expansion.Replace(text, match =>
	{
		var group = match.Groups;
		if (group[2].Success) return char.ConvertFromUtf32(Convert.ToInt32(group[2].Value, 16));
		if (group[3].Success) return Tags($"<{group[3].Value} {group[4].Value}");
		if (group[5].Success) return Tags($"</{group[5].Value}");
		return Tags($":{group[6].Value} {group[7].Value}");
	});

	private static IEnumerable<JsonElement[]> Section(string name) =>
		Cases.GetProperty(name).EnumerateArray().Select(row => row.EnumerateArray().ToArray());

	private static string Text(JsonElement value) => Expand(value.GetString()!);

	/// <summary>warnings as one comparable string: "message at 3; …"</summary>
	private static string Listed(IEnumerable<(string Message, int At)> warnings) =>
		string.Join("; ", warnings.Select(warning => $"{warning.Message} at {warning.At}"));

	private static string Listed(JsonElement warnings) =>
		Listed(warnings.EnumerateArray().Select(warning => (Text(warning[0]), warning[1].GetInt32())));

	private static string Listed(IEnumerable<UniscriptWarning> warnings) =>
		Listed(warnings.Select(warning => (warning.Message, warning.At)));

	[Fact]
	public void Converts()
	{
		foreach (var row in Section("converts"))
			Assert.Equal((Text(row[0]), Text(row[1])), (Text(row[0]), Uniscript.Convert(Text(row[0])).Text));
	}

	[Fact]
	public void Quiet()
	{
		foreach (var row in Section("quiet"))
		{
			var conversion = Uniscript.Convert(Text(row[0]));
			Assert.Equal((Text(row[0]), Text(row[1]), 0), (Text(row[0]), conversion.Text, conversion.Warnings.Count));
		}
	}

	[Fact]
	public void WarnCounts()
	{
		foreach (var row in Section("warnCounts"))
		{
			var conversion = Uniscript.Convert(Text(row[0]));
			Assert.Equal((Text(row[1]), row[2].GetInt32()), (conversion.Text, conversion.Warnings.Count));
		}
	}

	[Fact]
	public void RoundTrips()
	{
		foreach (var row in Section("roundTrips"))
		{
			Assert.Equal(Text(row[1]), Uniscript.ToUnicode(Text(row[0])));
			Assert.Equal(Text(row[0]), Uniscript.ToUniscript(Text(row[1])));
		}
	}

	[Fact]
	public void ToUniscript()
	{
		foreach (var row in Section("toUniscript")) Assert.Equal(Text(row[1]), Uniscript.ToUniscript(Text(row[0])));
	}

	[Fact]
	public void Explicit()
	{
		foreach (var row in Section("explicit")) Assert.Equal(Text(row[1]), Uniscript.Explicit(Text(row[0])));
	}

	[Fact]
	public void UnicodeRoundTrips()
	{
		foreach (var row in Section("unicodeRoundTrips"))
			Assert.Equal(Text(row[0]), Uniscript.ToUnicode(Uniscript.ToUniscript(Text(row[0]))));
	}

	[Fact]
	public void Warns()
	{
		foreach (var row in Section("warns"))
		{
			var (uniscript, message, at) = (Text(row[0]), Text(row[2]), row[3].GetInt32());
			var conversion = Uniscript.Convert(uniscript);
			Assert.Equal((Text(row[1]), $"{message} at {at}"), (conversion.Text, Listed(conversion.Warnings)));
			var error = Assert.Throws<UniscriptException>(() => Uniscript.Convert(uniscript, UniscriptMode.Error));
			Assert.Equal((UniscriptErrorKind.Unsupported, message, at, $"uniscript: {message} at byte {at}"),
				(error.Kind, error.Detail, error.At, error.Message));
		}
	}

	[Fact]
	public void Errors()
	{
		foreach (var row in Section("errors"))
		{
			var error = Assert.Throws<UniscriptException>(() => Uniscript.Convert(Text(row[0])));
			Assert.Equal((Text(row[0]), Enum.Parse<UniscriptErrorKind>(row[1].GetString()!), Text(row[2])),
				(Text(row[0]), error.Kind, error.Detail));
		}
	}

	[Fact]
	public void Lenient()
	{
		foreach (var row in Section("lenient"))
		{
			var conversion = Uniscript.Convert(Text(row[0]), UniscriptMode.Lenient);
			Assert.Equal((Text(row[1]), string.Join("; ", row[2].EnumerateArray().Select(Text))),
				(conversion.Text, string.Join("; ", conversion.Warnings.Select(warning => warning.Message))));
		}
	}

	[Fact]
	public void Header()
	{
		foreach (var row in Section("header"))
		{
			var expected = row[1].ValueKind == JsonValueKind.Null ? null : new UniscriptHeader(Text(row[1]), row[2].GetInt32());
			Assert.Equal(expected, Uniscript.Header(Text(row[0])));
		}
	}

	[Fact]
	public void Html()
	{
		foreach (var row in Section("html"))
		{
			var tagged = Uniscript.Convert(Text(row[0])).Text;
			Assert.Equal(Text(row[1]), Uniscript.Html(tagged).Text);
			Assert.Equal(Listed(row[2]), Listed(Uniscript.MetaRuns(tagged).Warnings));
		}
	}

	[Fact]
	public void MetaRuns()
	{
		foreach (var row in Section("metaRuns"))
		{
			var styled = Uniscript.MetaRuns(Text(row[0]));
			Assert.Equal((Text(row[1]), row[2].GetInt32(), Listed(row[3])), (styled.Text, styled.Runs.Count, Listed(styled.Warnings)));
		}
	}

	[Fact]
	public void Fonts()
	{
		foreach (var row in Section("fonts"))
		{
			var font = Uniscript.Font(Text(row[0]));
			if (row[1].ValueKind == JsonValueKind.Null) Assert.Null(font);
			else
			{
				Assert.Equal(Text(row[1]), font?.Lang);
				if (row[2].ValueKind == JsonValueKind.String) Assert.Equal(Text(row[2]), font!.Families[0]);
			}
		}
	}

	[Fact]
	public void Api()
	{
		Assert.Equal("α 𝔄", Uniscript.ToUnicode("\\:alpha \\:fracture-A"));
		Assert.Equal("\\:alpha \\:fracture-A", Uniscript.ToUniscript("α 𝔄"));
		Assert.Equal("\\:alpha <:color red A/>", Uniscript.Explicit("<:alpha> <:color red A>"));
		Assert.Equal("color: {}", Uniscript.MetaTemplate("color"));
		Assert.Null(Uniscript.MetaTemplate("nosuchkey"));
		Assert.Throws<ArgumentNullException>(() => Uniscript.Convert(null!));
		Assert.Throws<ArgumentException>(() => Uniscript.ToUniscript("a\0b"));
		Assert.Equal(Encoding.UTF8.GetByteCount("α "), Uniscript.MetaRuns(Uniscript.ToUnicode("α <:color red A>")).Runs[0].Start);
	}
}
