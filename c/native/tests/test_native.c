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

int main(void) {
	index_is_sorted_and_every_key_resolves();
	conversions_are_repeatable();
	printf("%s: native checks\n", failures ? "FAILED" : "OK");
	return failures != 0;
}
