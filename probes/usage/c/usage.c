#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "uniscript.h"

int main(void) {
	/* round trip; uniscript_to_unicode prints warnings to stderr and returns NULL on an error */
	char *unicode = uniscript_to_unicode("<:alpha> <:fracture A>");
	char *spelled = uniscript_to_uniscript("α 𝔄");
	assert(strcmp(unicode, "α 𝔄") == 0 && strcmp(spelled, "<:alpha> <:fracture A>") == 0);
	uniscript_free(unicode);
	uniscript_free(spelled);

	/* every tag form */
	const char *forms[][2] = {
		{"\\:alpha", "α"}, {"<:greek small letter alpha>", "α"}, {"<:double-R>", "ℝ"}, {"<:bold italic alpha>", "𝜶"},
		{"<:greek>athos<:/greek>", "αθοσ"}, {"<:greek>athos<:>", "αθοσ"}, {"<<::>alpha>", "<:alpha>"},
		{"\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"}, {"\\:1F60D", "😍"}, {"\\:bed", "🛏"},
	};
	for (size_t i = 0; i < sizeof forms / sizeof *forms; i++) {
		char *converted = uniscript_to_unicode(forms[i][0]);
		assert(strcmp(converted, forms[i][1]) == 0);
		uniscript_free(converted);
	}

	/* warnings and the modes UNISCRIPT_WARN, UNISCRIPT_ERROR and UNISCRIPT_LENIENT */
	uniscript_result result = uniscript_convert("<:fracture 7>", UNISCRIPT_WARN);
	assert(strcmp(result.text, "7") == 0 && result.warning_count == 1);
	assert(strcmp(result.warnings[0].message, "no fracture form of 7") == 0);
	uniscript_result_free(&result);
	result = uniscript_convert("<:fracture 7>", UNISCRIPT_ERROR);
	assert(result.text == NULL && result.error_kind == UNISCRIPT_UNSUPPORTED);
	uniscript_result_free(&result);
	result = uniscript_convert("<:nosuch>", UNISCRIPT_WARN);
	assert(result.error_kind == UNISCRIPT_UNKNOWN_ENTITY && strcmp(result.error_detail, "nosuch") == 0);
	uniscript_result_free(&result);
	result = uniscript_convert("<:nosuch>", UNISCRIPT_LENIENT);
	assert(strcmp(result.text, "<:nosuch>") == 0 && result.warning_count == 1);
	uniscript_result_free(&result);

	/* the header: version points into the source */
	const char *source = "<:uniscript version=\"https://uniscript.org/v1\">\n<:alpha>";
	const char *version;
	size_t version_length, length;
	assert(uniscript_header(source, &version, &version_length, &length));
	assert(strncmp(version, UNISCRIPT_VERSION, version_length) == 0 && version_length == strlen(UNISCRIPT_VERSION));
	result = uniscript_convert(source, UNISCRIPT_WARN);
	assert(strcmp(result.text, "α") == 0 && result.warning_count == 0);
	uniscript_result_free(&result);

	/* meta information */
	result = uniscript_convert("<:color red 𓀀>", UNISCRIPT_WARN);
	uniscript_styled styled = uniscript_meta_runs(result.text);
	assert(strcmp(styled.text, "𓀀") == 0 && styled.run_count == 1);
	assert(strcmp(styled.runs[0].key, "color") == 0 && strcmp(styled.runs[0].value, "red") == 0);
	uniscript_result html = uniscript_html(result.text);
	assert(strcmp(html.text, "<span style=\"color: red\">𓀀</span>") == 0);
	uniscript_result_free(&html);
	uniscript_styled_free(&styled);
	uniscript_result_free(&result);
	puts("c: ok");
	return 0;
}
