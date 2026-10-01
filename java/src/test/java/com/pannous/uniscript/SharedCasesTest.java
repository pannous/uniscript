package com.pannous.uniscript;

import com.pannous.uniscript.Uniscript.Mode;
import com.pannous.uniscript.Uniscript.Warning;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.TestFactory;
import org.junit.jupiter.api.function.ThrowingConsumer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** The cases every uniscript library shares, js/test/cases.json (format in its _format) */
class SharedCasesTest {
	private static final JSONObject CASES = load();
	private static final Pattern PLACEHOLDER = Pattern.compile("\\{(U\\+[0-9A-F]+|open \\S+ \\S+|close \\S+|attached \\S+ \\S+)\\}");
	private static final Map<String, String> META_SIGILS = Map.of("open", "<", "close", "</", "attached", ":");
	private static final int TAG_BASE = 0xE0000;
	private static final String CANCEL_TAG = Character.toString(0xE007F);

	private static JSONObject load() {
		try {
			return new JSONObject(Files.readString(Path.of(System.getProperty("uniscript.cases"))));
		} catch (IOException failure) {
			throw new IllegalStateException("no shared cases", failure);
		}
	}

	/** {U+E0072} → that code point, {open key value} → its TAG sequence */
	static String expanded(String value) {
		Matcher placeholder = PLACEHOLDER.matcher(value);
		return placeholder.replaceAll(match -> Matcher.quoteReplacement(tags(match.group(1))));
	}

	private static String tags(String placeholder) {
		String[] words = placeholder.split(" ");
		if (words[0].startsWith("U+")) return Character.toString(Integer.parseInt(words[0].substring(2), 16));
		String spelled = META_SIGILS.get(words[0]) + String.join(" ", List.of(words).subList(1, words.length));
		StringBuilder sequence = new StringBuilder();
		spelled.chars().forEach(character -> sequence.appendCodePoint(TAG_BASE + character));
		return sequence.append(CANCEL_TAG).toString();
	}

	private static String text(JSONArray item, int index) {
		return item.isNull(index) ? null : expanded(item.getString(index));
	}

	private static List<List<Object>> warningsOf(List<Warning> warnings) {
		return warnings.stream().map(warning -> List.<Object>of(warning.message(), warning.at())).toList();
	}

	private static List<List<Object>> expectedWarnings(JSONArray warnings) {
		List<List<Object>> expected = new ArrayList<>();
		for (int index = 0; index < warnings.length(); index++) {
			JSONArray warning = warnings.getJSONArray(index);
			expected.add(List.of(warning.getString(0), warning.getLong(1)));
		}
		return expected;
	}

	private static Stream<DynamicTest> cases(String kind, ThrowingConsumer<JSONArray> test) {
		JSONArray items = CASES.getJSONArray(kind);
		List<DynamicTest> tests = new ArrayList<>();
		for (int index = 0; index < items.length(); index++) {
			JSONArray item = items.getJSONArray(index);
			tests.add(DynamicTest.dynamicTest(kind + " " + item, () -> test.accept(item)));
		}
		return tests.stream();
	}

	@TestFactory
	Stream<DynamicTest> converts() {
		return Stream.concat(cases("converts", c -> assertEquals(text(c, 1), Uniscript.convert(text(c, 0), Mode.WARN).text())),
				cases("roundTrips", c -> assertEquals(text(c, 1), Uniscript.convert(text(c, 0), Mode.WARN).text())));
	}

	@TestFactory
	Stream<DynamicTest> quiet() {
		return cases("quiet", c -> assertEquals(new Uniscript.Result(text(c, 1), List.of()), Uniscript.convert(text(c, 0), Mode.WARN)));
	}

	@TestFactory
	Stream<DynamicTest> warnCounts() {
		return cases("warnCounts", c -> {
			Uniscript.Result result = Uniscript.convert(text(c, 0), Mode.WARN);
			assertEquals(text(c, 1), result.text());
			assertEquals(c.getInt(2), result.warnings().size());
		});
	}

	@TestFactory
	Stream<DynamicTest> roundTrips() {
		return cases("roundTrips", c -> assertEquals(text(c, 0), Uniscript.toUniscript(text(c, 1))));
	}

	@TestFactory
	Stream<DynamicTest> toUniscript() {
		return cases("toUniscript", c -> assertEquals(text(c, 1), Uniscript.toUniscript(text(c, 0))));
	}

	@TestFactory
	Stream<DynamicTest> unicodeRoundTrips() {
		return cases("unicodeRoundTrips", c -> assertEquals(text(c, 0), Uniscript.toUnicode(Uniscript.toUniscript(text(c, 0)))));
	}

	@TestFactory
	Stream<DynamicTest> warns() {
		return cases("warns", c -> {
			Warning warning = new Warning(text(c, 2), c.getLong(3));
			assertEquals(new Uniscript.Result(text(c, 1), List.of(warning)), Uniscript.convert(text(c, 0), Mode.WARN));
			UniscriptException error = assertThrows(UniscriptException.class, () -> Uniscript.convert(text(c, 0), Mode.ERROR));
			assertEquals(UniscriptException.Kind.UNSUPPORTED, error.kind());
			assertEquals(warning, error.warning());
		});
	}

	@TestFactory
	Stream<DynamicTest> errors() {
		return cases("errors", c -> {
			UniscriptException error = assertThrows(UniscriptException.class, () -> Uniscript.convert(text(c, 0), Mode.WARN));
			assertEquals(c.getString(1), kindName(error.kind()));
			assertEquals(text(c, 2), error.detail());
		});
	}

	/** UNKNOWN_ENTITY → UnknownEntity, the spelling of the cases */
	private static String kindName(UniscriptException.Kind kind) {
		StringBuilder name = new StringBuilder();
		for (String word : kind.name().split("_")) name.append(word.charAt(0)).append(word.substring(1).toLowerCase());
		return name.toString();
	}

	@TestFactory
	Stream<DynamicTest> lenient() {
		return cases("lenient", c -> {
			Uniscript.Result result = Uniscript.convert(text(c, 0), Mode.LENIENT);
			List<String> messages = c.getJSONArray(2).toList().stream().map(Object::toString).toList();
			assertEquals(text(c, 1), result.text());
			assertEquals(messages, result.warnings().stream().map(Warning::message).toList());
		});
	}

	@TestFactory
	Stream<DynamicTest> header() {
		return cases("header", c -> {
			var found = Uniscript.header(text(c, 0));
			if (c.isNull(1)) {
				assertTrue(found.isEmpty());
			} else {
				assertEquals(new Uniscript.Header(text(c, 1), c.getLong(2)), found.orElseThrow());
			}
		});
	}

	@TestFactory
	Stream<DynamicTest> html() {
		return cases("html", c -> {
			Uniscript.Result html = Uniscript.html(Uniscript.convert(text(c, 0), Mode.WARN).text());
			assertEquals(text(c, 1), html.text());
			assertEquals(expectedWarnings(c.getJSONArray(2)), warningsOf(html.warnings()));
		});
	}

	@TestFactory
	Stream<DynamicTest> metaRuns() {
		return cases("metaRuns", c -> {
			Uniscript.Styled styled = Uniscript.metaRuns(text(c, 0));
			assertEquals(text(c, 1), styled.text());
			assertEquals(c.getInt(2), styled.runs().size());
			assertEquals(expectedWarnings(c.getJSONArray(3)), warningsOf(styled.warnings()));
		});
	}

	@TestFactory
	Stream<DynamicTest> fonts() {
		return cases("fonts", c -> {
			var font = Uniscript.font(c.getString(0));
			if (c.isNull(1)) {
				assertTrue(font.isEmpty());
			} else {
				assertEquals(c.getString(1), font.orElseThrow().lang());
				if (!c.isNull(2)) assertEquals(c.getString(2), font.orElseThrow().families().getFirst());
			}
		});
	}
}
