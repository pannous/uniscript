/* A program built against an installed uniscript (make consumer-test): cc consumer.c $(pkg-config --cflags --libs uniscript) */
#include <stdio.h>
#include <string.h>
#include <uniscript.h>

int main(void) {
	char *text = uniscript_to_unicode("<:alpha> <:fracture A>");
	char *spelled = uniscript_to_uniscript(text);
	int ok = text && spelled && strcmp(text, "α 𝔄") == 0 && strcmp(spelled, "<:alpha> <:fracture A>") == 0;
	printf("%s C consumer: %s | %s\n", ok ? "ok  " : "FAIL", text, spelled);
	uniscript_free(text);
	uniscript_free(spelled);
	return !ok;
}
