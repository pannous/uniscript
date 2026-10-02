/* Native-only checks: the compiled-in index is well formed and every key resolves through the binary search */
#include "internal.h"
#include "uniscript.h"

#include <stdio.h>
#include <string.h>

static int failures;

static void check(int passed, const char *what) {
	if (passed) return;
	failures++;
	printf("FAIL %s\n", what);
}

static void index_is_sorted_and_every_key_resolves(void) {
	check(index_valid(), "index magic and table count");
	const char *names[TABLE_COUNT] = { "names", "chars", "suffixes", "fonts", "meta" };
	for (table in = 0; in < TABLE_COUNT; in++) {
		uint32_t previous_hash = 0;
		str previous_key = { "", 0 };
		size_t bad = 0;
		for (size_t position = 0; position < index_count(in); position++) {
			uint32_t hash;
			str key, value, found;
			index_record(in, position, &hash, &key, &value);
			size_t shorter = key.n < previous_key.n ? key.n : previous_key.n;
			int order = memcmp(previous_key.p, key.p, shorter);
			bool sorted = position == 0 || previous_hash < hash ||
			              (previous_hash == hash && (order < 0 || (order == 0 && previous_key.n < key.n)));
			bool resolves = index_get(in, key, &found) && found.p == value.p && found.n == value.n;
			if (hash != text_hash(key) || !sorted || !resolves || !utf8_valid(key.p, key.n) || !utf8_valid(value.p, value.n)) bad++;
			previous_hash = hash;
			previous_key = key;
		}
		char what[64];
		snprintf(what, sizeof what, "table %s: %zu bad records", names[in], bad);
		check(bad == 0 && index_count(in) > 0, what);
	}
}

/* Many conversions in a row reuse no state: the same input gives the same output */
static void conversions_are_repeatable(void) {
	for (int i = 0; i < 3; i++) {
		uniscript_result result = uniscript_convert("<:mirror red A> <:greek> athos <:/greek> <:nosuch>", UNISCRIPT_LENIENT);
		check(result.text && strcmp(result.text, "A\xF3\xA0\x81\xB2\xF3\xA0\x81\x8D \xCE\xB1\xCE\xB8\xCE\xBF\xCF\x83 <:nosuch>") == 0, "repeatable lenient conversion");
		check(result.warning_count == 1, "one warning");
		uniscript_result_free(&result);
	}
}

/* one warning per replaced subpart */
static void lenient_input(const char *source, const char *text, size_t warning_count, size_t first_at, const char *what) {
	uniscript_result result = uniscript_convert(source, UNISCRIPT_LENIENT);
	check(result.text && strcmp(result.text, text) == 0 && result.warning_count == warning_count &&
	          (!warning_count || result.warnings[0].at == first_at),
	      what);
	uniscript_result_free(&result);
	result = uniscript_convert(source, UNISCRIPT_WARN);
	check(result.error_kind == UNISCRIPT_INVALID_INPUT && !result.text, "invalid input is an error unless lenient");
	uniscript_result_free(&result);
}

/* LENIENT repairs invalid UTF-8 like Rust's from_utf8_lossy: each maximal invalid subpart becomes one U+FFFD */
static void lenient_mode_repairs_invalid_input(void) {
	lenient_input("a\xFF" "b<:alpha>", "a\xEF\xBF\xBD" "b\xCE\xB1", 1, 1, "stray byte");
	lenient_input("\xE2\x82<:beta>", "\xEF\xBF\xBD\xCE\xB2", 1, 0, "truncated sequence is one subpart");
	lenient_input("\xC0\x80", "\xEF\xBF\xBD\xEF\xBF\xBD", 2, 0, "overlong: two subparts");
	lenient_input("\xED\xA0\x80", "\xEF\xBF\xBD\xEF\xBF\xBD\xEF\xBF\xBD", 3, 0, "surrogate: three subparts");
	lenient_input("x\xF4\x90", "x\xEF\xBF\xBD\xEF\xBF\xBD", 2, 1, "above U+10FFFF");
	lenient_input(NULL, "", 1, 0, "NULL is empty");
	uniscript_result result = uniscript_convert("\xFF<:greek c>", UNISCRIPT_LENIENT);
	check(result.warning_count == 2 && strcmp(result.warnings[0].message, "invalid UTF-8 byte 0xFF replaced by U+FFFD") == 0 &&
	          strcmp(result.warnings[1].message, "no greek form of c") == 0 && result.warnings[1].at == 3,
	      "input warnings first, then those of the conversion at offsets of the repaired text");
	uniscript_result_free(&result);
}

int main(void) {
	lenient_mode_repairs_invalid_input();
	index_is_sorted_and_every_key_resolves();
	conversions_are_repeatable();
	printf("%s: native checks\n", failures ? "FAILED" : "OK");
	return failures != 0;
}
