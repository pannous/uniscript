/* Meta information in plain text: invisible TAG sequences U+E0020–E007E ended by CANCEL TAG U+E007F. The first
 * spelled character says what a sequence does: `<key value` opens a span, `</key` closes it, `:key value` attaches to
 * the character before it. Emoji tag sequences start with a letter or digit and pass through unchanged. */
#include "internal.h"

#include <ctype.h>
#include <string.h>

#define TAG_BASE 0xE0000u
#define TAG_TEXT_FIRST 0xE0020u
#define TAG_TEXT_LAST 0xE007Eu
#define ZERO_WIDTH_JOINER 0x200Du
/* besides ASCII letters and digits; no spaces, quotes, `;` or brackets, so values stay safe inside CSS and HTML */
static const char VALUE_PUNCTUATION[] = "#.%+-_,()/";

static const char *sigil_of(meta_kind kind) { return kind == META_OPEN ? "<" : kind == META_CLOSE ? "</" : ":"; }

void meta_tags(buf *out, meta_kind kind, str key, str value) {
	buf spelled = { 0 };
	buf_addz(&spelled, sigil_of(kind));
	buf_adds(&spelled, key);
	if (kind != META_CLOSE) {
		buf_addz(&spelled, " ");
		buf_adds(&spelled, value);
	}
	for (size_t i = 0; i < spelled.n; i++) buf_addc(out, TAG_BASE + (unsigned char)spelled.p[i]);
	buf_addc(out, CANCEL_TAG);
	buf_free(&spelled);
}

void meta_uniscript(buf *out, const meta *sequence) {
	switch (sequence->kind) {
	case META_OPEN: buf_addf(out, "<:%.*s %.*s>", S(sequence->key), S(sequence->value)); break;
	case META_CLOSE: buf_addf(out, "<:/%.*s>", S(sequence->key)); break;
	case META_ATTACHED: buf_addf(out, "%.*s %.*s", S(sequence->key), S(sequence->value)); break;
	}
}

static bool is_key(str key) {
	if (!key.n || !islower((unsigned char)key.p[0])) return false;
	for (size_t i = 0; i < key.n; i++) {
		unsigned char c = (unsigned char)key.p[i];
		if (!(islower(c) || isdigit(c) || c == '-')) return false;
	}
	return true;
}

bool is_meta_value(str value) {
	if (!value.n) return false;
	for (size_t i = 0; i < value.n; i++) {
		unsigned char c = (unsigned char)value.p[i];
		if (!(c < 0x80 && (isalnum(c) || strchr(VALUE_PUNCTUATION, c)))) return false;
	}
	return true;
}

/* A TAG sequence at the start of the text: its ASCII spelling and its byte length with the CANCEL TAG, 0 if none */
static size_t tag_sequence_at(str text, buf *spelled) {
	uint32_t character;
	size_t at = 0, length;
	while ((length = utf8_decode(str_from(text, at), &character))) {
		if (character == CANCEL_TAG) return spelled->n ? at + length : 0;
		if (character < TAG_TEXT_FIRST || character > TAG_TEXT_LAST) return 0;
		char ascii = (char)(character - TAG_BASE);
		buf_add(spelled, &ascii, 1);
		at += length;
	}
	return 0;
}

static bool parse_meta(meta *found) {
	str spelled = buf_str(&found->spelled);
	if (str_starts(spelled, "</")) {
		found->kind = META_CLOSE;
		found->key = str_from(spelled, 2);
		found->value = (str){ "", 0 };
		return is_key(found->key);
	}
	if (!spelled.n || (spelled.p[0] != '<' && spelled.p[0] != ':')) return false;
	found->kind = spelled.p[0] == '<' ? META_OPEN : META_ATTACHED;
	return split_once(str_from(spelled, 1), ' ', &found->key, &found->value) && is_key(found->key) && is_meta_value(found->value);
}

size_t meta_at(str text, meta *found) {
	*found = (meta){ 0 };
	size_t length = tag_sequence_at(text, &found->spelled);
	if (length && parse_meta(found)) return length;
	meta_free(found);
	return 0;
}

void meta_free(meta *sequence) { buf_free(&sequence->spelled); }

size_t emoji_tags_at(str text) {
	buf spelled = { 0 };
	size_t length = tag_sequence_at(text, &spelled);
	for (size_t i = 0; i < spelled.n; i++)
		if (!isalnum((unsigned char)spelled.p[i])) length = 0;
	buf_free(&spelled);
	return length;
}

/* Whether the character belongs to the character before it: marks, joiners, variation selectors, TAG characters */
bool extends(uint32_t previous, uint32_t c) {
	return previous == ZERO_WIDTH_JOINER || (previous >= 0x13430 && previous <= 0x13436) || (c >= 0x0300 && c <= 0x036F) ||
	       (c >= 0x1AB0 && c <= 0x1AFF) || (c >= 0x1DC0 && c <= 0x1DFF) || (c >= 0x20D0 && c <= 0x20FF) ||
	       (c >= 0xFE00 && c <= 0xFE0F) || (c >= 0xFE20 && c <= 0xFE2F) || c == ZERO_WIDTH_JOINER ||
	       (c >= 0x13430 && c <= 0x1345F) || (c >= 0x1F3FB && c <= 0x1F3FF) || (c >= 0xE0000 && c <= 0xE007F) ||
	       (c >= 0xE0100 && c <= 0xE01EF);
}

void meta_attach(buf *out, str text, str sequences) {
	uint32_t character, previous = NO_CHARACTER;
	size_t length;
	for (size_t at = 0; (length = utf8_decode(str_from(text, at), &character)); at += length) {
		if (previous != NO_CHARACTER && !extends(previous, character)) buf_adds(out, sequences);
		buf_add(out, text.p + at, length);
		previous = character;
	}
	buf_adds(out, sequences);
}

void escape_html(buf *out, str text) {
	for (size_t i = 0; i < text.n; i++) {
		switch (text.p[i]) {
		case '&': buf_addz(out, "&amp;"); break;
		case '<': buf_addz(out, "&lt;"); break;
		case '>': buf_addz(out, "&gt;"); break;
		case '"': buf_addz(out, "&quot;"); break;
		default: buf_add(out, text.p + i, 1);
		}
	}
}
