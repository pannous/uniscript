/* The reference cases (cases.h) through the C API; links against c/ffi or c/native */
#include "../uniscript.h"
#include "cases.h"

#include <stdio.h>

static int checks, failures;

static void check(int passed, const char *what, const char *input, const char *got, const char *expected) {
	checks++;
	if (passed) return;
	failures++;
	printf("FAIL %s: %s\n  got      %s\n  expected %s\n", what, input, got ? got : "(null)", expected ? expected : "(null)");
}

static int same(const char *a, const char *b) { return a && b ? strcmp(a, b) == 0 : a == b; }

static void check_text(const char *what, const char *input, const char *got, const char *expected) {
	check(same(got, expected), what, input, got, expected);
}

static void check_number(const char *what, const char *input, size_t got, size_t expected) {
	char got_text[32], expected_text[32];
	snprintf(got_text, sizeof got_text, "%zu", got);
	snprintf(expected_text, sizeof expected_text, "%zu", expected);
	check(got == expected, what, input, got_text, expected_text);
}

static void check_warnings(const char *input, const uniscript_warning *warnings, size_t count, const char *const *messages, size_t expected_count) {
	check_number("warning count", input, count, expected_count);
	for (size_t i = 0; i < count && i < expected_count; i++) check_text("warning", input, warnings[i].message, messages[i]);
}

static size_t message_count(const char *const *messages, size_t capacity) {
	size_t count = 0;
	while (count < capacity && messages[count]) count++;
	return count;
}

/* uniscript → the expected Unicode, without warnings */
static void test_converts(const conversion_case *c) {
	char *uniscript = expand_tags(c->uniscript), *unicode = expand_tags(c->unicode);
	uniscript_result result = uniscript_convert(uniscript, UNISCRIPT_WARN);
	check_text("convert", c->uniscript, result.text, unicode);
	check_warnings(c->uniscript, result.warnings, result.warning_count, NULL, 0);
	uniscript_result_free(&result);
	free(uniscript);
	free(unicode);
}

static void test_spells(const conversion_case *c) {
	char *unicode = expand_tags(c->unicode), *spelled = uniscript_to_uniscript(unicode);
	check_text("to_uniscript", c->unicode, spelled, c->uniscript);
	uniscript_free(spelled);
	free(unicode);
}

static void test_restores(const char *text) {
	char *unicode = expand_tags(text), *spelled = uniscript_to_uniscript(unicode), *back = uniscript_to_unicode(spelled);
	check_text("round trip", text, back, unicode);
	uniscript_free(spelled);
	uniscript_free(back);
	free(unicode);
}

static void test_warns(const warning_case *c) {
	char *unicode = expand_tags(c->unicode);
	uniscript_result result = uniscript_convert(c->uniscript, UNISCRIPT_WARN);
	check_text("warned text", c->uniscript, result.text, unicode);
	check_warnings(c->uniscript, result.warnings, result.warning_count, &c->message, 1);
	if (result.warning_count) check_number("warning at", c->uniscript, result.warnings[0].at, c->at);
	uniscript_result_free(&result);
	result = uniscript_convert(c->uniscript, UNISCRIPT_ERROR);
	check_number("unsupported kind", c->uniscript, result.error_kind, UNISCRIPT_UNSUPPORTED);
	check_text("unsupported detail", c->uniscript, result.error_detail, c->message);
	check_number("unsupported at", c->uniscript, result.error_at, c->at);
	check(result.text == NULL, "no text on error", c->uniscript, result.text, NULL);
	uniscript_result_free(&result);
	free(unicode);
}

static void test_fails(const error_case *c) {
	uniscript_result result = uniscript_convert(c->uniscript, UNISCRIPT_WARN);
	check_number("error kind", c->uniscript, result.error_kind, (size_t)c->kind);
	check_text("error detail", c->uniscript, result.error_detail, c->detail);
	check_text("error", c->uniscript, result.error, c->error);
	uniscript_result_free(&result);
	check(uniscript_to_unicode(c->uniscript) == NULL, "to_unicode NULL on error", c->uniscript, NULL, NULL);
}

static void test_lenient(const lenient_case *c) {
	uniscript_result result = uniscript_convert(c->uniscript, UNISCRIPT_LENIENT);
	check_text("lenient", c->uniscript, result.text, c->unicode);
	check_warnings(c->uniscript, result.warnings, result.warning_count, c->messages, message_count(c->messages, 3));
	uniscript_result_free(&result);
}

static void test_finds_header(const header_case *c) {
	const char *version = NULL;
	size_t version_length = 99, length = 99;
	int found = uniscript_header(c->source, &version, &version_length, &length);
	check_number("header found", c->source, (size_t)found, (size_t)c->found);
	if (!found) return;
	check(version_length == strlen(c->version) && strncmp(version, c->version, version_length) == 0, "header version", c->source, version, c->version);
	check_number("header length", c->source, length, c->length);
}

static void test_renders(const html_case *c) {
	char *tagged = expand_tags(c->tagged), *html = expand_tags(c->html);
	uniscript_result result = uniscript_html(tagged);
	int passed = result.text && (c->contains ? strstr(result.text, html) != NULL : strcmp(result.text, html) == 0);
	check(passed, "html", c->tagged, result.text, html);
	check_warnings(c->tagged, result.warnings, result.warning_count, &c->message, c->message ? 1 : 0);
	if (c->message && result.warning_count) check_number("html warning at", c->tagged, result.warnings[0].at, c->at);
	uniscript_result_free(&result);
	free(tagged);
	free(html);
}

static void test_finds_font(const font_case *c) {
	uniscript_font font = {0};
	int found = uniscript_font_lookup(c->name, &font);
	check_number("font found", c->name, (size_t)found, c->lang != NULL);
	if (!found) return;
	check_text("font name", c->name, font.name, c->name);
	check_text("font lang", c->name, font.lang, c->lang);
	if (c->first_family) check_text("font family", c->name, font.family_count ? font.families[0] : NULL, c->first_family);
	if (c->first_feature) check_text("font feature", c->name, font.feature_count ? font.features[0] : NULL, c->first_feature);
	uniscript_font_free(&font);
	check(font.name == NULL && font.families == NULL, "font freed", c->name, NULL, NULL);
}

static void emoji_tags_are_no_meta(void) {
	char *scotland = expand_tags(SCOTLAND), *spelled = uniscript_to_uniscript(scotland);
	check(strstr(spelled, "green") == NULL, "no green suffix in", SCOTLAND, spelled, NULL);
	uniscript_styled styled = uniscript_meta_runs(scotland);
	check_text("styled text", SCOTLAND, styled.text, scotland);
	check_number("runs", SCOTLAND, styled.run_count, 0);
	uniscript_styled_free(&styled);
	uniscript_free(spelled);
	free(scotland);
}

static void meta_runs_nest(void) {
	char *tagged = expand_tags("x{<font cuneiform-hittite}𒀭A{:color red}{</font}");
	uniscript_styled styled = uniscript_meta_runs(tagged);
	check_text("styled text", tagged, styled.text, "x𒀭A");
	check_number("runs", tagged, styled.run_count, 2);
	if (styled.run_count == 2) {
		check_text("run key", tagged, styled.runs[0].key, "font");
		check_text("run value", tagged, styled.runs[0].value, "cuneiform-hittite");
		check_number("run start", tagged, styled.runs[0].start, 1);
		check_number("run end", tagged, styled.runs[0].end, 6);
		check_text("attached key", tagged, styled.runs[1].key, "color");
		check_number("attached start", tagged, styled.runs[1].start, 5);
	}
	uniscript_styled_free(&styled);
	free(tagged);
}

static void edges(void) {
	char *template = uniscript_meta_template("color");
	check_text("meta template", "color", template, "color: {}");
	uniscript_free(template);
	check(uniscript_meta_template("blink") == NULL, "no meta template", "blink", NULL, NULL);
	uniscript_result invalid = uniscript_convert("\xff<:alpha>", UNISCRIPT_LENIENT);
	check_number("invalid UTF-8", "\\xff", invalid.error_kind, UNISCRIPT_INVALID_INPUT);
	uniscript_result_free(&invalid);
	invalid = uniscript_convert(NULL, UNISCRIPT_WARN);
	check_number("NULL input", "NULL", invalid.error_kind, UNISCRIPT_INVALID_INPUT);
	uniscript_result_free(&invalid);
	uniscript_result_free(NULL);
	uniscript_free(NULL);
	check(uniscript_to_uniscript(NULL) == NULL, "to_uniscript(NULL)", "NULL", NULL, NULL);
	check_text("version", "UNISCRIPT_VERSION", UNISCRIPT_VERSION, "https://uniscript.org/v1");
}

#define EACH(table, test) for (size_t i = 0; i < COUNT(table); i++) test(&table[i])

int main(void) {
	EACH(round_trips, test_converts);
	EACH(round_trips, test_spells);
	EACH(converts, test_converts);
	EACH(spells_back, test_spells);
	for (size_t i = 0; i < COUNT(restores); i++) test_restores(restores[i]);
	EACH(warns, test_warns);
	EACH(errors, test_fails);
	EACH(lenients, test_lenient);
	EACH(headers, test_finds_header);
	EACH(htmls, test_renders);
	EACH(fonts, test_finds_font);
	emoji_tags_are_no_meta();
	meta_runs_nest();
	edges();
	printf("C: %d checks, %d failures\n", checks, failures);
	return failures != 0;
}
