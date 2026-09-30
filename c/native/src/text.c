/* Byte slices, growable buffers and UTF-8 */
#include "internal.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *checked_alloc(void *pointer) {
	if (!pointer) {
		fputs("uniscript: out of memory\n", stderr);
		abort();
	}
	return pointer;
}

str str_of(const char *text) { return (str){ text, strlen(text) }; }

str str_from(str text, size_t start) { return (str){ text.p + start, text.n - start }; }

str str_slice(str text, size_t start, size_t end) { return (str){ text.p + start, end - start }; }

bool str_eq(str text, const char *other) { return strlen(other) == text.n && memcmp(text.p, other, text.n) == 0; }

bool str_starts(str text, const char *prefix) {
	size_t n = strlen(prefix);
	return n <= text.n && memcmp(text.p, prefix, n) == 0;
}

size_t str_find(str text, char byte) {
	const char *found = text.n ? memchr(text.p, byte, text.n) : NULL;
	return found ? (size_t)(found - text.p) : text.n;
}

bool split_once(str text, char separator, str *before, str *after) {
	size_t at = str_find(text, separator);
	if (at == text.n) return false;
	*before = str_slice(text, 0, at);
	*after = str_from(text, at + 1);
	return true;
}

/* Unicode White_Space, as Rust's char::is_whitespace */
bool is_whitespace(uint32_t c) {
	return (c >= 0x09 && c <= 0x0D) || c == 0x20 || c == 0x85 || c == 0xA0 || c == 0x1680 || (c >= 0x2000 && c <= 0x200A) ||
	       c == 0x2028 || c == 0x2029 || c == 0x202F || c == 0x205F || c == 0x3000;
}

str trim_start(str text) {
	uint32_t character;
	size_t length;
	while ((length = utf8_decode(text, &character)) && is_whitespace(character)) text = str_from(text, length);
	return text;
}

/* the byte length of the whitespace at the end */
static size_t trailing_whitespace(str text) {
	size_t end = text.n;
	while (end > 0) {
		size_t start = end - 1;
		while (start > 0 && ((unsigned char)text.p[start] & 0xC0) == 0x80) start--;
		uint32_t character;
		utf8_decode(str_slice(text, start, end), &character);
		if (!is_whitespace(character)) break;
		end = start;
	}
	return text.n - end;
}

str trim(str text) {
	text = trim_start(text);
	text.n -= trailing_whitespace(text);
	return text;
}

void buf_add(buf *out, const char *bytes, size_t n) {
	if (out->n + n + 1 > out->cap) {
		out->cap = (out->n + n + 1) * 2;
		out->p = checked_alloc(realloc(out->p, out->cap));
	}
	if (n) memcpy(out->p + out->n, bytes, n);
	out->n += n;
	out->p[out->n] = 0;
}

void buf_adds(buf *out, str text) { buf_add(out, text.p, text.n); }

void buf_addz(buf *out, const char *text) { buf_add(out, text, strlen(text)); }

void buf_addc(buf *out, uint32_t character) {
	char bytes[5];
	buf_add(out, bytes, utf8_encode(character, bytes));
}

void buf_addf(buf *out, const char *format, ...) {
	va_list arguments, again;
	va_start(arguments, format);
	va_copy(again, arguments);
	int n = vsnprintf(NULL, 0, format, arguments);
	va_end(arguments);
	buf_add(out, "", 0);
	if (out->n + (size_t)n + 1 > out->cap) {
		out->cap = (out->n + (size_t)n + 1) * 2;
		out->p = checked_alloc(realloc(out->p, out->cap));
	}
	vsnprintf(out->p + out->n, (size_t)n + 1, format, again);
	va_end(again);
	out->n += (size_t)n;
}

str buf_str(const buf *text) { return (str){ text->p ? text->p : "", text->n }; }

char *buf_take(buf *text) {
	buf_add(text, "", 0);
	char *taken = text->p;
	*text = (buf){ 0 };
	return taken;
}

void buf_free(buf *text) {
	free(text->p);
	*text = (buf){ 0 };
}

char *copy_of(str text) {
	buf copy = { 0 };
	buf_adds(&copy, text);
	return buf_take(&copy);
}

size_t utf8_decode(str text, uint32_t *character) {
	if (!text.n) return 0;
	const unsigned char *b = (const unsigned char *)text.p;
	size_t length = b[0] < 0x80 ? 1 : b[0] < 0xE0 ? 2 : b[0] < 0xF0 ? 3 : 4;
	if (length > text.n) length = text.n;
	uint32_t c = length == 1 ? b[0] : b[0] & (0x3F >> (length - 1));
	for (size_t i = 1; i < length; i++) c = c << 6 | (b[i] & 0x3F);
	*character = c;
	return length;
}

size_t utf8_encode(uint32_t c, char out[5]) {
	size_t n = c < 0x80 ? 1 : c < 0x800 ? 2 : c < 0x10000 ? 3 : 4;
	static const unsigned char lead[] = { 0, 0, 0xC0, 0xE0, 0xF0 };
	for (size_t i = n - 1; i > 0; i--, c >>= 6) out[i] = (char)(0x80 | (c & 0x3F));
	out[0] = (char)(n == 1 ? c : lead[n] | c);
	out[n] = 0;
	return n;
}

/* well-formed UTF-8 (RFC 3629): no overlongs, surrogates or code points above U+10FFFF */
bool utf8_valid(const char *text, size_t n) {
	const unsigned char *b = (const unsigned char *)text;
	for (size_t i = 0; i < n;) {
		unsigned char c = b[i];
		size_t length = c < 0x80 ? 1 : (c >= 0xC2 && c <= 0xDF) ? 2 : (c >= 0xE0 && c <= 0xEF) ? 3 : (c >= 0xF0 && c <= 0xF4) ? 4 : 0;
		if (!length || i + length > n) return false;
		for (size_t k = 1; k < length; k++)
			if ((b[i + k] & 0xC0) != 0x80) return false;
		if ((c == 0xE0 && b[i + 1] < 0xA0) || (c == 0xED && b[i + 1] > 0x9F) || (c == 0xF0 && b[i + 1] < 0x90) ||
		    (c == 0xF4 && b[i + 1] > 0x8F))
			return false;
		i += length;
	}
	return true;
}

uint32_t first_character(str text) {
	uint32_t character;
	return utf8_decode(text, &character) ? character : NO_CHARACTER;
}
