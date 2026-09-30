/* uniscript "<:alpha>"        → α
 * uniscript -r "α"            → <:alpha>        (--strict: unsupported characters are errors; --lenient: no errors)
 * echo "<:alpha>" | uniscript → α (stdin when no text is given)
 * uniscript --html "<:font cuneiform-hittite>𒀭<:/font>"   meta information as <span lang style> instead of TAG sequences
 * The command line of the Rust crate (src/main.rs) over the native C library */
#include "uniscript.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *const FLAGS[] = { "-r", "--reverse", "--strict", "--html", "--lenient" };
#define FLAG_COUNT (sizeof FLAGS / sizeof *FLAGS)

static int has_flag(int argc, char **argv, const char *wanted) {
	for (int i = 1; i < argc; i++)
		if (strcmp(argv[i], wanted) == 0) return 1;
	return 0;
}

static int is_flag(const char *argument) {
	for (size_t i = 0; i < FLAG_COUNT; i++)
		if (strcmp(argument, FLAGS[i]) == 0) return 1;
	return 0;
}

static char *appended(char *text, size_t *length, const char *more, size_t more_length) {
	text = realloc(text, *length + more_length + 1);
	if (!text) abort();
	memcpy(text + *length, more, more_length);
	*length += more_length;
	text[*length] = 0;
	return text;
}

/* the words joined by spaces, or stdin when there are none */
static char *input_text(int argc, char **argv) {
	char *text = appended(NULL, &(size_t){ 0 }, "", 0);
	size_t length = 0;
	int words = 0;
	for (int i = 1; i < argc; i++) {
		if (is_flag(argv[i])) continue;
		if (words++) text = appended(text, &length, " ", 1);
		text = appended(text, &length, argv[i], strlen(argv[i]));
	}
	if (words) return text;
	char chunk[65536];
	size_t read;
	while ((read = fread(chunk, 1, sizeof chunk, stdin))) text = appended(text, &length, chunk, read);
	return text;
}

static void print_warnings(const uniscript_warning *warnings, size_t count) {
	for (size_t i = 0; i < count; i++) fprintf(stderr, "warning: uniscript: %s at byte %zu\n", warnings[i].message, warnings[i].at);
}

static int print_line(char *text) {
	size_t length = strlen(text);
	fputs(text, stdout);
	if (!length || text[length - 1] != '\n') fputc('\n', stdout);
	uniscript_free(text);
	return 0;
}

int main(int argc, char **argv) {
	if (argc > 1 && (!strcmp(argv[1], "-h") || !strcmp(argv[1], "--help"))) {
		puts("uniscript \"<:alpha>\" → α; -r reverse; --strict, --lenient, --html; stdin when no text is given");
		return 0;
	}
	char *text = input_text(argc, argv);
	if (has_flag(argc, argv, "-r") || has_flag(argc, argv, "--reverse")) {
		char *converted = uniscript_to_uniscript(text);
		free(text);
		if (!converted) return fputs("uniscript: invalid UTF-8\n", stderr), 1;
		return print_line(converted);
	}
	int strict = has_flag(argc, argv, "--strict");
	uniscript_mode mode = strict ? UNISCRIPT_ERROR : has_flag(argc, argv, "--lenient") ? UNISCRIPT_LENIENT : UNISCRIPT_WARN;
	uniscript_result result = uniscript_convert(text, mode);
	free(text);
	if (!result.text) {
		fprintf(stderr, "%s\n", result.error);
		uniscript_result_free(&result);
		return 1;
	}
	if (has_flag(argc, argv, "--html")) {
		uniscript_result html = uniscript_html(result.text);
		if (strict && (result.warning_count || html.warning_count)) {
			const uniscript_warning *first = result.warning_count ? result.warnings : html.warnings;
			fprintf(stderr, "uniscript: %s at byte %zu\n", first->message, first->at);
			uniscript_result_free(&result);
			uniscript_result_free(&html);
			return 1;
		}
		print_warnings(result.warnings, result.warning_count);
		print_warnings(html.warnings, html.warning_count);
		uniscript_result_free(&result);
		result = html;
	} else {
		print_warnings(result.warnings, result.warning_count);
	}
	char *converted = result.text;
	result.text = NULL;
	uniscript_result_free(&result);
	return print_line(converted);
}
