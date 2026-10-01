/* Uniscript → Unicode and back, a plain C port of the Rust crate (src/lib.rs, src/meta.rs): entities (<:alpha>,
 * \:infinity), block types (<:fracture A>, <:greek> a b <:/greek>), suffix controls (<:mirror red A>), groups
 * (<:beside 犭 句>) and meta information (<:font han-japanese> … <:/font>, <:color #ff8800 A>) as TAG sequences */
#include "uniscript.h"
#include "internal.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define HEADER_OPEN "<:uniscript"
#define VERSION_ATTRIBUTE "version=\""
#define VERSION_PREFIX "https://uniscript.org/v"
#define ESCAPED_COLON "<::>"
#define ESCAPED_UNICODE "<:U>"
#define MAX_HEX_DIGITS 8
/* bare hex (\:1F60D) and \U1F60D need at least 4 digits, so a mistyped short name stays unknown */
#define MIN_BARE_HEX_DIGITS 4
#define MAX_CODE_POINT 0x10FFFFu
#define SURROGATE_FIRST 0xD800u
#define SURROGATE_LAST 0xDFFFu
#define FONT_KEY "font"
#define LANG_KEY "lang"
#define VALUE_PLACEHOLDER "{}"
#define CLOSE_SPAN "</span>"
#define SUFFIX_KEY "*suffix"
#define GROUP_KEY "*group"
#define MAX_OPERAND_WORDS 8 /* the most words one operand spans: <:egyptian man with hand to mouth> */
/* the block control naming the meta a block becomes where it has no suffix control (red *meta → color red) */
#define META_FALLBACK_KEY "*meta"
#define REPLACEMENT_CHARACTER 0xFFFDu

typedef struct { str *items; size_t n, cap; } strs;

typedef struct {
	uniscript_warning *warnings;
	size_t warning_count, warning_capacity;
	uniscript_error_kind error;
	char *detail;
	size_t error_at;
} converter;

static void *grown(void *items, size_t *capacity, size_t count, size_t size) {
	if (count < *capacity) return items;
	*capacity = *capacity ? *capacity * 2 : 8;
	void *more = realloc(items, *capacity * size);
	if (!more) abort();
	return more;
}

static void strs_push(strs *list, str item) {
	list->items = grown(list->items, &list->cap, list->n, sizeof *list->items);
	list->items[list->n++] = item;
}

static void add_warning(uniscript_warning **warnings, size_t *count, size_t *capacity, char *message, size_t at) {
	*warnings = grown(*warnings, capacity, *count, sizeof **warnings);
	(*warnings)[(*count)++] = (uniscript_warning){ message, at };
}

static void warn(converter *self, size_t at, const char *format, ...) __attribute__((format(printf, 3, 4)));
static void warn(converter *self, size_t at, const char *format, ...) {
	char *message = NULL;
	va_list arguments;
	va_start(arguments, format);
	int n = vsnprintf(NULL, 0, format, arguments);
	va_end(arguments);
	message = malloc((size_t)n + 1);
	if (!message) abort();
	va_start(arguments, format);
	vsnprintf(message, (size_t)n + 1, format, arguments);
	va_end(arguments);
	add_warning(&self->warnings, &self->warning_count, &self->warning_capacity, message, at);
}

static bool fail(converter *self, uniscript_error_kind kind, str detail) {
	free(self->detail);
	self->error = kind;
	self->detail = copy_of(detail);
	return false;
}

static void clear_error(converter *self) {
	free(self->detail);
	self->detail = NULL;
	self->error = UNISCRIPT_OK;
}

static void error_text(buf *out, uniscript_error_kind kind, const char *detail, size_t at) {
	switch (kind) {
	case UNISCRIPT_UNKNOWN_ENTITY: buf_addf(out, "unknown uniscript entity: %s", detail); break;
	case UNISCRIPT_UNCLOSED: buf_addf(out, "unclosed <: at %s", detail); break;
	case UNISCRIPT_UNSUPPORTED: buf_addf(out, "uniscript: %s at byte %zu", detail, at); break;
	case UNISCRIPT_INVALID_META: buf_addf(out, "invalid meta value in <:%s>", detail); break;
	case UNISCRIPT_INVALID_INPUT: buf_addz(out, "uniscript input is NULL or invalid UTF-8"); break;
	case UNISCRIPT_OK: break;
	}
}

static bool name(str key, str *value) { return index_get(TABLE_NAMES, key, value); }

static bool is_block(str block) { return index_getf(TABLE_NAMES, NULL, "%.*s ", S(block)); }

static bool meta_template(str key, str *template) { return index_get(TABLE_META, key, template); }

/* The script a character needs its own controls for: hieroglyphs, and CJK ideographs, radicals and strokes */
static const char *script_of(uint32_t c) {
	if (c >= 0x13000 && c <= 0x13FFF) return "egyptian";
	if ((c >= 0x2E80 && c <= 0x2FFF) || (c >= 0x3000 && c <= 0x9FFF) || (c >= 0x20000 && c <= 0x33FFF)) return "cjk";
	return "";
}

static bool is_name_character(char c) {
	return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' || c == '_';
}

/* Bytes of the name token at the start of the text; the + of a leading U+ belongs to it */
static size_t token_length(str text) {
	size_t length = str_starts(text, "U+") || str_starts(text, "u+") ? 2 : 0;
	while (length < text.n && is_name_character(text.p[length])) length++;
	return length;
}

/* The value of minimum–8 hex digits */
static bool hex_value(str digits, size_t minimum, uint32_t *value) {
	if (digits.n < minimum || digits.n > MAX_HEX_DIGITS) return false;
	*value = 0;
	for (size_t i = 0; i < digits.n; i++) {
		char c = digits.p[i];
		int digit = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
		if (digit < 0) return false;
		*value = *value * 16 + (uint32_t)digit;
	}
	return true;
}

/* The value of a code point token: U+1F60D, U1F60D, 0x1F60D in any case (1–8 hex digits) or bare 1F60D (4–8) */
static bool code_point_value(str token, uint32_t *value) {
	static const char *const prefixes[] = { "U+", "u+", "0x", "0X", "U", "u" }; /* U+ before U */
	for (size_t i = 0; i < sizeof prefixes / sizeof *prefixes; i++)
		if (str_starts(token, prefixes[i])) return hex_value(str_from(token, strlen(prefixes[i])), 1, value);
	return hex_value(token, MIN_BARE_HEX_DIGITS, value);
}

/* Bytes after the backslash of \U1F60D (4–8 hex digits as a whole name token), the only marker without a colon; 0 for none */
static size_t unicode_escape(str after_backslash) {
	if (!str_starts(after_backslash, "U")) return 0;
	size_t length = token_length(str_from(after_backslash, 1));
	uint32_t value;
	return hex_value(str_slice(after_backslash, 1, 1 + length), MIN_BARE_HEX_DIGITS, &value) ? 1 + length : 0;
}

static size_t character_count(str text) {
	size_t count = 0;
	for (size_t i = 0; i < text.n; i++) count += ((unsigned char)text.p[i] & 0xC0) != 0x80;
	return count;
}

/* The control a block puts after a character of its script, or after any character; an empty one: the effect cannot
 * apply to that script */
static bool suffix_of(str block, uint32_t character, str *suffix) {
	const char *script = script_of(character);
	return (*script && index_getf(TABLE_NAMES, suffix, "%.*s " SUFFIX_KEY " %s", S(block), script)) ||
	       index_getf(TABLE_NAMES, suffix, "%.*s " SUFFIX_KEY, S(block));
}

/* The control of an effect after one character into suffixes; without one, a block with a *meta fallback (the colors:
 * red *meta → color red) puts that attached meta sequence into metas, anything else nothing; both warn */
static void effect_control(converter *self, buf *suffixes, buf *metas, str block, uint32_t character, size_t at) {
	str suffix, fallback, key, value;
	if (suffix_of(block, character, &suffix) && suffix.n) {
		buf_adds(suffixes, suffix);
		return;
	}
	char spelled[5];
	utf8_encode(character, spelled);
	if (index_getf(TABLE_NAMES, &fallback, "%.*s " META_FALLBACK_KEY, S(block)) && split_once(fallback, ' ', &key, &value)) {
		warn(self, at, "%.*s on %s kept as %.*s meta", S(block), spelled, S(key));
		meta_tags(metas, META_ATTACHED, key, value);
		return;
	}
	warn(self, at, "%.*s does not apply to %s", S(block), spelled);
}

/* The suffix controls of the stacked effect words (mirror in <:mirror red A>) for one character, then the meta
 * sequences of the effects it has no control for: a meta follows the character's suffix controls */
static void effect_suffixes(converter *self, buf *out, strs effects, uint32_t character, size_t at) {
	buf metas = { 0 };
	for (size_t i = 0; i < effects.n; i++) effect_control(self, out, &metas, effects.items[i], character, at);
	buf_adds(out, buf_str(&metas));
	buf_free(&metas);
}

/* One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects.
 * A character the block has neither for stays plain, with a warning. */
static void styled(converter *self, buf *out, str block, uint32_t character, strs effects, size_t at) {
	char spelled[5];
	utf8_encode(character, spelled);
	str own, suffix;
	if (index_getf(TABLE_NAMES, &own, "%.*s %s", S(block), spelled)) {
		buf_adds(out, own);
	} else if (!suffix_of(block, character, &suffix)) {
		warn(self, at, "no %.*s form of %s", S(block), spelled);
		buf_addz(out, spelled);
	} else {
		strs blocks = { 0 };
		strs_push(&blocks, block);
		for (size_t i = 0; i < effects.n; i++) strs_push(&blocks, effects.items[i]);
		buf_addz(out, spelled);
		effect_suffixes(self, out, blocks, character, at);
		free(blocks.items);
		return;
	}
	effect_suffixes(self, out, effects, character, at);
}

static size_t characters_of(str text, uint32_t **characters) {
	*characters = malloc((text.n + 1) * sizeof **characters);
	if (!*characters) abort();
	size_t count = 0, length;
	for (size_t at = 0; (length = utf8_decode(str_from(text, at), &(*characters)[count])); at += length) count++;
	return count;
}

/* One operand: its own entry (red circle → 🔴, greek eta → η), else each character or pair (greek th → θ) of the
 * operand, or of the entity it names */
static void operand(converter *self, buf *out, str block, str token, strs effects, size_t at) {
	str own, named;
	if (index_getf(TABLE_NAMES, &own, "%.*s %.*s", S(block), S(token))) {
		uint32_t first = first_character(own);
		buf_adds(out, own);
		effect_suffixes(self, out, effects, first == NO_CHARACTER ? ' ' : first, at);
		return;
	}
	uint32_t *characters;
	size_t count = characters_of(name(token, &named) && token.n > 1 ? named : token, &characters);
	for (size_t i = 0; i < count;) {
		if (i + 1 < count) {
			char first[5], second[5];
			utf8_encode(characters[i], first);
			utf8_encode(characters[i + 1], second);
			if (index_getf(TABLE_NAMES, &own, "%.*s %s%s", S(block), first, second)) {
				buf_adds(out, own);
				effect_suffixes(self, out, effects, characters[i], at);
				i += 2;
				continue;
			}
		}
		styled(self, out, block, characters[i++], effects, at);
	}
	free(characters);
}

/* The next token of text split on the byte separator, empty tokens skipped; false at the end */
static bool next_token(str *rest, char separator, str *token) {
	while (rest->n && rest->p[0] == separator) *rest = str_from(*rest, 1);
	if (!rest->n) return false;
	size_t end = str_find(*rest, separator);
	*token = str_slice(*rest, 0, end);
	*rest = str_from(*rest, end);
	return true;
}

/* The next whitespace separated word of rest; false at the end */
static bool next_word(str *rest, str *word) {
	uint32_t character;
	size_t length, start = 0, end;
	while ((length = utf8_decode(str_from(*rest, start), &character)) && is_whitespace(character)) start += length;
	for (end = start; (length = utf8_decode(str_from(*rest, end), &character)) && !is_whitespace(character);) end += length;
	*word = str_slice(*rest, start, end);
	*rest = str_from(*rest, end);
	return word->n > 0;
}

/* A block with a suffix control (mirror, red), which stacks as an effect instead of restyling */
static bool is_effect(str block) { return index_getf(TABLE_NAMES, NULL, "%.*s " SUFFIX_KEY, S(block)); }

static bool form(str block, str operand_text, str *found) {
	return index_getf(TABLE_NAMES, found, "%.*s %.*s", S(block), S(operand_text));
}

/* The next operand of the block (none: the next word) in rest, hyphenated into token: the longest run of words that
 * names one operand (seated man, red crown), else one word */
static bool next_operand(const str *block, str *rest, buf *token) {
	str words[MAX_OPERAND_WORDS], after[MAX_OPERAND_WORDS], left = *rest;
	size_t count = 0;
	while (count < (block ? MAX_OPERAND_WORDS : 1) && next_word(&left, &words[count])) after[count++] = left;
	for (size_t n = count; n > 0; n--) {
		token->n = 0;
		for (size_t i = 0; i < n; i++) {
			if (i) buf_addz(token, "-");
			buf_adds(token, words[i]);
		}
		if (n == 1 || form(*block, buf_str(token), NULL)) {
			*rest = after[n - 1];
			return true;
		}
	}
	return false;
}

/* Whether the content starts with an operand of the block: <:egyptian red crown> names a sign, red is no effect */
static bool starts_operand(str block, str content) {
	buf token = { 0 };
	bool starts = next_operand(&block, &content, &token) && form(block, buf_str(&token), NULL);
	buf_free(&token);
	return starts;
}

/* The space separated operands of an inline tag, spaces dropped */
static void operands(converter *self, buf *out, str block, str content, strs effects, size_t at) {
	buf token = { 0 };
	for (str rest = content; next_operand(&block, &rest, &token);) operand(self, out, block, buf_str(&token), effects, at);
	buf_free(&token);
}

static bool is_group(str block) { return index_getf(TABLE_NAMES, NULL, "%.*s " GROUP_KEY, S(block)); }

/* A group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the script of
 * the first part has; the parts are operands of the naming block (<:egyptian above A1 A2>), else names or text */
static void group(converter *self, buf *out, str group_name, const str *naming, str content, size_t at) {
	buf token = { 0 };
	str part, infix = { 0 }, prefix;
	bool has_infix = false;
	for (size_t position = 0; next_operand(naming, &content, &token); position++) {
		str written = buf_str(&token);
		if (!(naming && form(*naming, written, &part)) && !(written.n > 1 && name(written, &part))) part = written;
		if (position == 0) {
			uint32_t first = first_character(part);
			const char *script = first == NO_CHARACTER ? "" : script_of(first);
			bool has_prefix = index_getf(TABLE_NAMES, &prefix, "%.*s *prefix %s", S(group_name), script);
			has_infix = index_getf(TABLE_NAMES, &infix, "%.*s *infix %s", S(group_name), script);
			if (has_prefix) buf_adds(out, prefix);
			if (!has_prefix && !has_infix) warn(self, at, "no %.*s group of %.*s", S(group_name), S(part));
		} else if (has_infix) {
			buf_adds(out, infix);
		}
		buf_adds(out, part);
	}
	buf_free(&token);
}

/* The block and plain operand a character spells back as: 𝐚 → (bold, a), α → ("", alpha) */
static bool spelling(uint32_t character, str *own, str *operand_text) {
	char bytes[5];
	str content, block, rest;
	if (!index_get(TABLE_CHARS, (str){ bytes, utf8_encode(character, bytes) }, &content)) return false;
	if (!str_starts(content, "<:") || content.n < 3 || content.p[content.n - 1] != '>') return false;
	content = str_slice(content, 2, content.n - 1);
	bool styled_form = split_once(content, ' ', &block, &rest) && is_block(block);
	*own = styled_form ? block : (str){ "", 0 };
	*operand_text = styled_form ? rest : content;
	return true;
}

/* The entity an operand of several characters names (alpha → α), else the operand itself */
static str base_of(str operand_text) {
	str named;
	return character_count(operand_text) > 1 && name(operand_text, &named) ? named : operand_text;
}

static int by_bytes(const void *a, const void *b) {
	const str *x = a, *y = b;
	int order = memcmp(x->p, y->p, x->n < y->n ? x->n : y->n);
	return order ? order : (x->n > y->n) - (x->n < y->n);
}

/* The next order of the parts in lexicographic order, false after the last */
static bool next_permutation(str *parts, size_t count) {
	size_t i = count - 1;
	while (i > 0 && by_bytes(&parts[i - 1], &parts[i]) >= 0) i--;
	if (i == 0) return false;
	size_t k = count - 1;
	while (by_bytes(&parts[k], &parts[i - 1]) <= 0) k--;
	str swap = parts[i - 1];
	parts[i - 1] = parts[k];
	parts[k] = swap;
	for (size_t low = i, high = count - 1; low < high; low++, high--) swap = parts[low], parts[low] = parts[high], parts[high] = swap;
	return true;
}

/* The block that combines styles in any order: bold + sans + italic → sans-bold-italic */
static bool combined(strs styles, buf *block) {
	strs parts = { 0 };
	for (size_t i = 0; i < styles.n; i++)
		for (str rest = styles.items[i], part; next_token(&rest, '-', &part);) strs_push(&parts, part);
	bool found = false;
	if (parts.n) {
		qsort(parts.items, parts.n, sizeof *parts.items, by_bytes);
		size_t distinct = 1;
		for (size_t i = 1; i < parts.n; i++)
			if (by_bytes(&parts.items[distinct - 1], &parts.items[i])) parts.items[distinct++] = parts.items[i];
		do {
			block->n = 0;
			for (size_t i = 0; i < distinct; i++) buf_addf(block, "%s%.*s", i ? "-" : "", S(parts.items[i]));
			found = is_block(buf_str(block));
		} while (!found && next_permutation(parts.items, distinct));
	}
	free(parts.items);
	return found;
}

static bool added(buf *out, str text) {
	buf_adds(out, text);
	return true;
}

/* A character in one further style (greek on 𝐚 → bold of greek a → 𝛂), commuting with its own style */
static bool restyled_by(str style, uint32_t character, buf *out) {
	char bytes[5];
	str found, own, operand_text;
	if (form(style, (str){ bytes, utf8_encode(character, bytes) }, &found)) return added(out, found);
	if (!spelling(character, &own, &operand_text)) return false;
	if (!own.n) return form(style, operand_text, &found) && added(out, found); /* greek alpha → α */
	str base = base_of(operand_text);
	if (character_count(base) != 1) return false;
	buf restyled = { 0 };
	bool ok = restyled_by(style, first_character(base), &restyled);
	if (ok && str_eq(base, restyled.p)) buf_addz(out, bytes);
	else if (ok) ok = form(own, buf_str(&restyled), &found) && added(out, found);
	buf_free(&restyled);
	return ok;
}

/* A character in further styles: in the block combining them with its own style (bold on 𝛼 → bold-italic α), else
 * one style after the other, each commuting with the character's own style where they do not combine. A style that
 * cannot apply keeps the character, with a warning. */
static void restyled(converter *self, buf *out, strs styles, uint32_t character, size_t at) {
	str own, operand_text, found;
	if (spelling(character, &own, &operand_text)) {
		strs all = { 0 };
		for (size_t i = 0; i < styles.n; i++) strs_push(&all, styles.items[i]);
		if (own.n) strs_push(&all, own);
		buf block = { 0 };
		str base = own.n ? base_of(operand_text) : operand_text;
		bool done = combined(all, &block) && form(buf_str(&block), base, &found);
		if (done) buf_adds(out, found);
		buf_free(&block);
		free(all.items);
		if (done) return;
	}
	buf text = { 0 }, next = { 0 };
	buf_addc(&text, character);
	for (size_t i = styles.n; i-- > 0;) {
		str current = buf_str(&text);
		if (character_count(current) != 1) continue;
		uint32_t single = first_character(current);
		next.n = 0;
		if (restyled_by(styles.items[i], single, &next)) {
			buf swap = text;
			text = next, next = swap;
		} else {
			warn(self, at, "no %.*s form of %.*s", S(styles.items[i]), S(current));
		}
	}
	buf_adds(out, buf_str(&text));
	buf_free(&text);
	buf_free(&next);
}

/* The text of a full block (<:greek> … <:/greek>) as written: each word an operand, the whitespace after it kept */
static void block_text(converter *self, buf *out, str block, str text, size_t at) {
	if (is_group(block)) {
		group(self, out, block, NULL, text, at);
		return;
	}
	uint32_t character;
	size_t word_end = 0, length;
	for (size_t position = 0; (length = utf8_decode(str_from(text, position), &character)); position += length) {
		if (!is_whitespace(character)) continue;
		operand(self, out, block, str_slice(text, word_end, position), (strs){ 0 }, at);
		buf_add(out, text.p + position, length);
		word_end = position + length;
	}
	if (word_end < text.n) operand(self, out, block, str_from(text, word_end), (strs){ 0 }, at);
}

static bool is_font(str name_of_font) { return index_getf(TABLE_FONTS, NULL, "%.*s ", S(name_of_font)); }

static bool tag(converter *self, buf *out, str content, size_t at);

/* The characters a meta attaches to: a tag content (mirror A, alpha), else space separated names and texts */
static bool meta_operands(converter *self, buf *out, str rest, size_t at) {
	buf text = { 0 };
	bool tagged = tag(self, &text, rest, at);
	if (tagged) buf_adds(out, buf_str(&text));
	buf_free(&text);
	if (tagged) return true;
	clear_error(self);
	str token;
	while (next_token(&rest, ' ', &token)) {
		bool is_name = token.n > 1;
		for (size_t i = 0; i < token.n; i++) is_name = is_name && is_name_character(token.p[i]);
		if (!is_name)
			buf_adds(out, token);
		else if (!tag(self, out, token, at))
			return false;
	}
	return true;
}

/* <:key value …> with meta keys: <:font han-japanese> opens spans, <:color #ff8800 mirror A> attaches to each
 * character of the rest; *handled false when the content starts with no meta key and value */
static bool meta_tag(converter *self, buf *out, str content, size_t at, bool *handled) {
	strs keys = { 0 }, values = { 0 };
	str rest = trim_start(content), key, after, value;
	bool ok = true;
	while (split_once(rest, ' ', &key, &after) && meta_template(key, NULL)) {
		after = trim_start(after);
		if (!split_once(after, ' ', &value, &rest)) value = after, rest = (str){ "", 0 };
		if (!is_meta_value(value)) {
			ok = fail(self, UNISCRIPT_INVALID_META, content);
			break;
		}
		if (str_eq(key, FONT_KEY) && !is_font(value))
			warn(self, at, "%.*s is no font style of the entities, used as a font family", S(value));
		strs_push(&keys, key);
		strs_push(&values, value);
		rest = trim_start(rest);
	}
	*handled = ok && keys.n;
	if (*handled) {
		buf sequences = { 0 };
		for (size_t i = 0; i < keys.n; i++) meta_tags(&sequences, rest.n ? META_ATTACHED : META_OPEN, keys.items[i], values.items[i]);
		if (!rest.n) {
			buf_adds(out, buf_str(&sequences));
		} else {
			buf text = { 0 };
			ok = meta_operands(self, &text, rest, at);
			if (ok) meta_attach(out, buf_str(&text), buf_str(&sequences));
			buf_free(&text);
		}
		buf_free(&sequences);
	}
	free(keys.items);
	free(values.items);
	return ok;
}

/* The character of a code point token (U+1F60D, 1F60D); an invalid one (surrogate, above 10FFFF) warns and stays
 * `written`; false for no code point token */
static bool code_point(converter *self, buf *out, str token, str written, size_t at) {
	uint32_t value;
	if (!code_point_value(token, &value)) return false;
	if (value <= MAX_CODE_POINT && (value < SURROGATE_FIRST || value > SURROGATE_LAST)) {
		buf_addc(out, value);
	} else {
		warn(self, at, "invalid code point U+%04X", value);
		buf_adds(out, written);
	}
	return true;
}

/* The text of <:content> at byte `at` that is no block opener or closer */
static bool tag(converter *self, buf *out, str content, size_t at) {
	if (content.n == 1) { /* <:<> <::> escape the marker */
		buf_adds(out, content);
		return true;
	}
	buf hyphenated = { 0 };
	buf_adds(&hyphenated, content);
	for (size_t i = 0; i < hyphenated.n; i++)
		if (hyphenated.p[i] == ' ') hyphenated.p[i] = '-';
	str text;
	bool named = name(buf_str(&hyphenated), &text);
	buf_free(&hyphenated);
	if (named) {
		buf_adds(out, text);
		return true;
	}
	buf written = { 0 };
	buf_addf(&written, "<:%.*s>", S(content));
	bool coded = code_point(self, out, content, buf_str(&written), at);
	buf_free(&written);
	if (coded) return true;
	bool handled;
	if (!meta_tag(self, out, content, at, &handled)) return false;
	if (handled) return true;
	size_t split = str_find(content, ' ');
	if (split == content.n) split = str_find(content, '-');
	str first = str_slice(content, 0, split < content.n ? split : 0);
	if (split < content.n && is_block(first)) {
		/* <:mirror red A>: effect words stack, the last takes the operands, the others add their suffixes; a word that
		 * starts an operand of the block before it is no block (<:egyptian red crown>) */
		strs words = { 0 };
		strs_push(&words, first);
		str rest = str_from(content, split + 1), word, after;
		while (split_once(rest, ' ', &word, &after) && is_block(word) && !starts_operand(words.items[words.n - 1], rest)) {
			strs_push(&words, word);
			rest = after;
		}
		size_t group_at = 0;
		while (group_at < words.n && !is_group(words.items[group_at])) group_at++;
		if (group_at < words.n) { /* <:egyptian above A1 A2>: the other block names the parts of the group */
			str group_name = words.items[group_at];
			memmove(&words.items[group_at], &words.items[group_at + 1], (words.n - group_at - 1) * sizeof(str));
			words.n--;
			size_t naming = words.n;
			while (naming > 0 && is_effect(words.items[naming - 1])) naming--;
			group(self, out, group_name, naming ? &words.items[naming - 1] : NULL, rest, at);
			free(words.items);
			return true;
		}
		str block = words.items[--words.n];
		strs effects = { 0 }, styles = { 0 };
		for (size_t i = 0; i < words.n; i++) strs_push(is_effect(words.items[i]) ? &effects : &styles, words.items[i]);
		if (!styles.n) {
			operands(self, out, block, rest, effects, at);
		} else { /* <:bold italic A>: the other style words restyle the operands of the last */
			buf plain = { 0 };
			operands(self, &plain, block, rest, (strs){ 0 }, at);
			uint32_t character;
			size_t length;
			for (str left = buf_str(&plain); (length = utf8_decode(left, &character)); left = str_from(left, length)) {
				restyled(self, out, styles, character, at);
				effect_suffixes(self, out, effects, character, at);
			}
			buf_free(&plain);
		}
		free(words.items);
		free(effects.items);
		free(styles.items);
		return true;
	}
	return fail(self, UNISCRIPT_UNKNOWN_ENTITY, content);
}

/* The source text of an error, with a warning, in UNISCRIPT_LENIENT; else the error */
static bool kept(converter *self, buf *out, str source, size_t at, uniscript_mode mode) {
	if (mode != UNISCRIPT_LENIENT) return false;
	buf message = { 0 };
	error_text(&message, self->error, self->detail, self->error_at);
	add_warning(&self->warnings, &self->warning_count, &self->warning_capacity, buf_take(&message), at);
	clear_error(self);
	buf_adds(out, source);
	return true;
}

int uniscript_header(const char *source, const char **version, size_t *version_length, size_t *length) {
	if (!source) return 0;
	str text = str_of(source), rest = str_from(text, 0), found = { "", 0 }, before, after;
	if (!str_starts(text, HEADER_OPEN)) return 0;
	rest = str_from(text, strlen(HEADER_OPEN));
	if (!rest.n || (rest.p[0] != ' ' && rest.p[0] != '>')) return 0;
	size_t close = str_find(rest, '>');
	if (close == rest.n) return 0;
	str attributes = str_slice(rest, 0, close);
	const char *attribute = strstr(source, VERSION_ATTRIBUTE);
	if (attribute && attribute < attributes.p + attributes.n) {
		before = str_from(attributes, (size_t)(attribute - attributes.p) + strlen(VERSION_ATTRIBUTE));
		found = split_once(before, '"', &found, &after) ? found : before;
	}
	size_t end = strlen(HEADER_OPEN) + close + 1;
	str tail = str_from(text, end);
	size_t line_break = str_starts(tail, "\r\n") ? 2 : str_starts(tail, "\n") ? 1 : 0;
	if (version) *version = found.p;
	if (version_length) *version_length = found.n;
	if (length) *length = end + line_break;
	return 1;
}

/* Every uniscript.org version is read (backwards compatible): empty, or VERSION_PREFIX and ASCII digits */
static bool reads_version(str version) {
	if (!version.n) return true;
	if (!str_starts(version, VERSION_PREFIX) || version.n == strlen(VERSION_PREFIX)) return false;
	for (size_t i = strlen(VERSION_PREFIX); i < version.n; i++)
		if (version.p[i] < '0' || version.p[i] > '9') return false;
	return true;
}

/* Bytes of the header to skip; a version that is no uniscript.org version warns */
static size_t header_length(converter *self, const char *source) {
	const char *version;
	size_t version_length, length;
	if (!uniscript_header(source, &version, &version_length, &length)) return 0;
	str found = { version, version_length };
	if (!reads_version(found)) warn(self, 0, "unsupported uniscript version %.*s", S(found));
	return length;
}

/* The start of the next <:, \: or \U1F60D marker, or the end */
static size_t marker_in(str rest) {
	for (size_t at = 0; at + 1 < rest.n; at++) {
		if ((rest.p[at] == '<' || rest.p[at] == '\\') && rest.p[at + 1] == ':') return at;
		if (rest.p[at] == '\\' && unicode_escape(str_from(rest, at + 1))) return at;
	}
	return rest.n;
}

static bool unicode_of(converter *self, buf *out, const char *text, uniscript_mode mode) {
	str source = str_of(text), block = { NULL, 0 }, empty = { 0 };
	for (size_t position = header_length(self, text); position < source.n;) {
		str rest = str_from(source, position);
		size_t marker = marker_in(rest);
		if (block.p)
			block_text(self, out, block, str_slice(rest, 0, marker), position);
		else
			buf_adds(out, str_slice(rest, 0, marker));
		position += marker;
		rest = str_from(source, position);
		if (!rest.n) break;
		size_t escape = unicode_escape(str_from(rest, 1));
		if (escape) {
			code_point(self, out, str_slice(rest, 2, 1 + escape), str_slice(rest, 0, 1 + escape), position);
			position += 1 + escape;
			continue;
		}
		if (rest.p[0] == '\\') {
			size_t name_end = 2 + token_length(str_from(rest, 2));
			str entity = str_slice(rest, 2, name_end), found, written = str_slice(rest, 0, name_end);
			if (name(entity, &found))
				buf_adds(out, found);
			else if (!code_point(self, out, entity, written, position) && !(fail(self, UNISCRIPT_UNKNOWN_ENTITY, entity), kept(self, out, written, position, mode)))
				return false;
			position += name_end;
			continue;
		}
		size_t close = str_find(str_from(rest, 2), '>') + 2;
		if (close >= rest.n) {
			fail(self, UNISCRIPT_UNCLOSED, rest);
			return kept(self, out, rest, position, mode);
		}
		str content = str_slice(rest, 2, close), key = str_from(content, content.n ? 1 : 0);
		if (str_starts(content, "/") && meta_template(key, NULL))
			meta_tags(out, META_CLOSE, key, empty);
		else if (!content.n || content.p[0] == '/')
			block = (str){ NULL, 0 };
		else if (is_block(content))
			block = content;
		else if (!tag(self, out, content, position) && !kept(self, out, str_slice(rest, 0, close + 1), position, mode))
			return false;
		position += close + 1;
	}
	return true;
}

static void free_warnings(uniscript_warning *warnings, size_t count) {
	for (size_t i = 0; i < count; i++) free(warnings[i].message);
	free(warnings);
}

static bool invalid(const char *text) { return !text || !utf8_valid(text, strlen(text)) || !index_valid(); }

static uniscript_result failed(uniscript_error_kind kind, const char *detail, size_t at) {
	uniscript_result result = { .error_kind = kind, .error_at = at };
	buf message = { 0 };
	error_text(&message, kind, detail ? detail : "", at);
	result.error = buf_take(&message);
	result.error_detail = copy_of(str_of(detail ? detail : ""));
	return result;
}

/* The source with each maximal invalid UTF-8 subpart replaced by U+FFFD, a warning at its offset for each; "" with a
 * warning for NULL */
static char *repaired(converter *self, const char *source) {
	buf text = { 0 };
	if (!source) {
		warn(self, 0, "input is NULL");
		return buf_take(&text);
	}
	size_t n = strlen(source), length;
	for (size_t at = 0; at < n; at += length) {
		if (utf8_sequence(source + at, n - at, &length)) {
			buf_add(&text, source + at, length);
			continue;
		}
		warn(self, at, "invalid UTF-8 byte 0x%02X replaced by U+FFFD", (unsigned char)source[at]);
		buf_addc(&text, REPLACEMENT_CHARACTER);
	}
	return buf_take(&text);
}

uniscript_result uniscript_convert(const char *source, uniscript_mode mode) {
	converter self = { 0 };
	char *lenient_source = NULL;
	if (!index_valid() || (mode != UNISCRIPT_LENIENT && invalid(source))) return failed(UNISCRIPT_INVALID_INPUT, NULL, 0);
	if (invalid(source)) source = lenient_source = repaired(&self, source);
	buf out = { 0 };
	uniscript_result result;
	if (!unicode_of(&self, &out, source, mode)) {
		result = failed(self.error, self.detail, 0);
		free_warnings(self.warnings, self.warning_count);
	} else if (mode == UNISCRIPT_ERROR && self.warning_count) {
		result = failed(UNISCRIPT_UNSUPPORTED, self.warnings[0].message, self.warnings[0].at);
		free_warnings(self.warnings, self.warning_count);
	} else {
		result = (uniscript_result){ .text = buf_take(&out), .warnings = self.warnings, .warning_count = self.warning_count };
	}
	buf_free(&out);
	free(self.detail);
	free(lenient_source);
	return result;
}

char *uniscript_to_unicode(const char *source) {
	uniscript_result result = uniscript_convert(source, UNISCRIPT_WARN);
	for (size_t i = 0; i < result.warning_count; i++)
		fprintf(stderr, "warning: uniscript: %s at byte %zu\n", result.warnings[i].message, result.warnings[i].at);
	char *text = result.text;
	result.text = NULL;
	uniscript_result_free(&result);
	return text;
}

/* One character and the block types of the suffix controls after it: <:mirror red A>, <:mirror red circle> */
static void spelled(buf *out, uint32_t character, strs blocks) {
	char bytes[5];
	utf8_encode(character, bytes);
	str own, inner = str_of(bytes);
	bool has_own = index_get(TABLE_CHARS, inner, &own);
	if (!blocks.n) {
		buf_adds(out, has_own ? own : inner);
		return;
	}
	if (has_own) inner = str_slice(own, 2, own.n - 1);
	buf_addz(out, "<:");
	for (size_t i = 0; i < blocks.n; i++) buf_addf(out, "%.*s ", S(blocks.items[i]));
	buf_addf(out, "%.*s>", S(inner));
}

/* A meta sequence of a known key at the start of the text: its length, 0 if none */
static size_t known_meta_at(str text, meta *found) {
	size_t length = meta_at(text, found);
	if (length && !meta_template(found->key, NULL)) {
		meta_free(found);
		return 0;
	}
	return length;
}

char *uniscript_to_uniscript(const char *text) {
	if (invalid(text)) return NULL;
	buf out = { 0 }, attached = { 0 }, form = { 0 };
	str rest = str_of(text);
	uint32_t character;
	size_t length;
	meta sequence;
	strs suffixes = { 0 };
	while ((length = utf8_decode(rest, &character))) {
		size_t meta_length = known_meta_at(rest, &sequence);
		if (meta_length && sequence.kind != META_ATTACHED) {
			meta_uniscript(&out, &sequence);
			meta_free(&sequence);
			rest = str_from(rest, meta_length);
			continue;
		}
		if (meta_length) meta_free(&sequence);
		rest = str_from(rest, length);
		if ((character == '<' || character == '\\') && str_starts(rest, ":")) {
			rest = str_from(rest, 1);
			buf_addc(&out, character);
			buf_addz(&out, ESCAPED_COLON);
			continue;
		}
		if (character == '\\' && unicode_escape(rest)) {
			rest = str_from(rest, 1);
			buf_addc(&out, character);
			buf_addz(&out, ESCAPED_UNICODE);
			continue;
		}
		size_t emoji = emoji_tags_at(rest);
		if (emoji) {
			spelled(&out, character, (strs){ 0 });
			buf_adds(&out, str_slice(rest, 0, emoji)); /* emoji tag sequences (subdivision flags) stay as they are */
			rest = str_from(rest, emoji);
			continue;
		}
		/* suffixes s1 s2 … are spelled "s2 … s1": the last word styles first, the others follow in order */
		suffixes.n = 0;
		uint32_t next;
		size_t next_length;
		str block;
		while ((next_length = utf8_decode(rest, &next)) && index_get(TABLE_SUFFIXES, str_slice(rest, 0, next_length), &block)) {
			strs_push(&suffixes, block);
			rest = str_from(rest, next_length);
		}
		if (suffixes.n) {
			str first = suffixes.items[0];
			memmove(suffixes.items, suffixes.items + 1, (suffixes.n - 1) * sizeof *suffixes.items);
			suffixes.items[suffixes.n - 1] = first;
		}
		attached.n = 0;
		while ((meta_length = known_meta_at(rest, &sequence))) {
			bool is_attached = sequence.kind == META_ATTACHED;
			if (is_attached) {
				if (attached.n) buf_addz(&attached, " ");
				meta_uniscript(&attached, &sequence);
				rest = str_from(rest, meta_length);
			}
			meta_free(&sequence);
			if (!is_attached) break;
		}
		form.n = 0;
		spelled(&form, character, suffixes);
		if (!attached.n) {
			buf_adds(&out, buf_str(&form));
		} else if (str_starts(buf_str(&form), "<:") && form.p[form.n - 1] == '>') {
			buf_addf(&out, "<:%.*s %.*s>", S(buf_str(&attached)), S(str_slice(buf_str(&form), 2, form.n - 1)));
		} else {
			buf_addf(&out, "<:%.*s %.*s>", S(buf_str(&attached)), S(buf_str(&form)));
		}
	}
	free(suffixes.items);
	buf_free(&attached);
	buf_free(&form);
	return buf_take(&out);
}

char *uniscript_meta_template(const char *key) {
	str template;
	return !invalid(key) && meta_template(str_of(key), &template) ? copy_of(template) : NULL;
}

/* The comma separated items of a font field, trimmed, empty ones dropped */
static size_t list_of(str text, char ***items) {
	size_t count = 0;
	*items = NULL;
	for (str rest = text, item; rest.n;) {
		if (!split_once(rest, ',', &item, &rest)) item = rest, rest = (str){ "", 0 };
		item = trim(item);
		if (!item.n) continue;
		*items = realloc(*items, (count + 1) * sizeof **items);
		if (!*items) abort();
		(*items)[count++] = copy_of(item);
	}
	return count;
}

int uniscript_font_lookup(const char *font_name, uniscript_font *font) {
	str key;
	if (invalid(font_name) || !font) return 0;
	str wanted = str_of(font_name), ignored, lang = { "", 0 }, families = lang, features = lang;
	if (!index_getf(TABLE_FONTS, &ignored, "%s ", font_name)) return 0;
	buf spaced = { 0 };
	buf_addf(&spaced, "%s ", font_name);
	index_entry(TABLE_FONTS, buf_str(&spaced), &key, &ignored);
	buf_free(&spaced);
	index_getf(TABLE_FONTS, &lang, "%.*s lang", S(wanted));
	index_getf(TABLE_FONTS, &families, "%.*s families", S(wanted));
	index_getf(TABLE_FONTS, &features, "%.*s features", S(wanted));
	*font = (uniscript_font){ .name = copy_of(trim(key)), .lang = copy_of(lang) };
	font->family_count = list_of(families, &font->families);
	font->feature_count = list_of(features, &font->features);
	return 1;
}

static int by_start_then_longest(const uniscript_meta_run *a, const uniscript_meta_run *b) {
	return a->start != b->start ? (a->start < b->start ? -1 : 1) : a->end != b->end ? (a->end > b->end ? -1 : 1) : 0;
}

/* stable insertion sorts: runs by (start, longest first), warnings by offset */
static void sort_runs(uniscript_meta_run *runs, size_t count) {
	for (size_t i = 1; i < count; i++)
		for (size_t k = i; k > 0 && by_start_then_longest(&runs[k - 1], &runs[k]) > 0; k--) {
			uniscript_meta_run swap = runs[k];
			runs[k] = runs[k - 1];
			runs[k - 1] = swap;
		}
}

static void sort_warnings(uniscript_warning *warnings, size_t count) {
	for (size_t i = 1; i < count; i++)
		for (size_t k = i; k > 0 && warnings[k - 1].at > warnings[k].at; k--) {
			uniscript_warning swap = warnings[k];
			warnings[k] = warnings[k - 1];
			warnings[k - 1] = swap;
		}
}

static uniscript_meta_run new_run(str key, str value, size_t start, size_t end, size_t at) {
	return (uniscript_meta_run){ copy_of(key), copy_of(value), start, end, at };
}

/* Reads the meta sequences out of tagged text. A span closing over spans opened after it closes them too and reopens
 * them, so runs always nest; a close without its open is a warning. */
uniscript_styled uniscript_meta_runs(const char *tagged) {
	uniscript_styled styled = { 0 };
	if (invalid(tagged)) return styled;
	size_t run_capacity = 0, warning_capacity = 0, open_count = 0, open_capacity = 0, cluster_start = 0;
	size_t *open = NULL;
	buf text = { 0 };
	str rest = str_of(tagged);
	uint32_t character, previous = NO_CHARACTER;
	meta sequence;
	for (size_t position = 0, length; (length = utf8_decode(str_from(rest, position), &character));) {
		size_t at = position, meta_length = meta_at(str_from(rest, position), &sequence);
		if (!meta_length) {
			if (!extends(previous, character)) cluster_start = text.n;
			buf_add(&text, rest.p + position, length);
			previous = character;
			position += length;
			continue;
		}
		position += meta_length;
		size_t here = text.n;
		styled.runs = grown(styled.runs, &run_capacity, styled.run_count, sizeof *styled.runs);
		if (sequence.kind == META_OPEN) {
			open = grown(open, &open_capacity, open_count, sizeof *open);
			open[open_count++] = styled.run_count;
			styled.runs[styled.run_count++] = new_run(sequence.key, sequence.value, here, here, at);
		} else if (sequence.kind == META_ATTACHED) {
			styled.runs[styled.run_count++] = new_run(sequence.key, sequence.value, cluster_start, here, at);
		} else {
			size_t matching = open_count;
			while (matching > 0 && !str_eq(sequence.key, styled.runs[open[matching - 1]].key)) matching--;
			if (!matching) {
				char *message = NULL;
				buf warning = { 0 };
				buf_addf(&warning, "</%.*s closes no open %.*s", S(sequence.key), S(sequence.key));
				message = buf_take(&warning);
				add_warning(&styled.warnings, &styled.warning_count, &warning_capacity, message, at);
			} else {
				size_t first_closed = matching - 1, closed_count = open_count - first_closed;
				size_t *closed = malloc(closed_count * sizeof *closed);
				if (!closed) abort();
				memcpy(closed, open + first_closed, closed_count * sizeof *closed);
				open_count = first_closed;
				for (size_t i = 0; i < closed_count; i++) styled.runs[closed[i]].end = here;
				for (size_t i = 1; i < closed_count; i++) {
					uniscript_meta_run reopened = styled.runs[closed[i]];
					styled.runs = grown(styled.runs, &run_capacity, styled.run_count, sizeof *styled.runs);
					open = grown(open, &open_capacity, open_count, sizeof *open);
					open[open_count++] = styled.run_count;
					styled.runs[styled.run_count++] = new_run(str_of(reopened.key), str_of(reopened.value), here, here, at);
				}
				free(closed);
			}
		}
		meta_free(&sequence);
	}
	for (size_t i = 0; i < open_count; i++) styled.runs[open[i]].end = text.n;
	free(open);
	size_t kept_runs = 0;
	for (size_t i = 0; i < styled.run_count; i++) {
		if (styled.runs[i].start < styled.runs[i].end) {
			styled.runs[kept_runs++] = styled.runs[i];
		} else {
			free(styled.runs[i].key);
			free(styled.runs[i].value);
		}
	}
	styled.run_count = kept_runs;
	sort_runs(styled.runs, styled.run_count);
	for (size_t i = 0; i < styled.run_count; i++) {
		if (meta_template(str_of(styled.runs[i].key), NULL)) continue;
		buf warning = { 0 };
		buf_addf(&warning, "unknown meta key %s", styled.runs[i].key);
		add_warning(&styled.warnings, &styled.warning_count, &warning_capacity, buf_take(&warning), styled.runs[i].at);
	}
	sort_warnings(styled.warnings, styled.warning_count);
	styled.text = buf_take(&text);
	return styled;
}

static void attribute(buf *out, const char *attribute_name, str value) {
	buf_addf(out, " %s=\"", attribute_name);
	escape_html(out, value);
	buf_addz(out, "\"");
}

static void quoted(buf *out, char **items, size_t count) {
	for (size_t i = 0; i < count; i++) buf_addf(out, "%s'%s'", i ? ", " : "", items[i]);
}

/* A CSS declaration from the template of a meta key, the value in place of {} */
static void declaration(buf *out, str template, str value) {
	for (str rest = template; rest.n;) {
		const char *found = NULL;
		for (size_t i = 0; i + 1 < rest.n && !found; i++)
			if (!memcmp(rest.p + i, VALUE_PLACEHOLDER, 2)) found = rest.p + i;
		if (!found) {
			buf_adds(out, rest);
			break;
		}
		buf_add(out, rest.p, (size_t)(found - rest.p));
		buf_adds(out, value);
		rest = str_from(rest, (size_t)(found - rest.p) + 2);
	}
}

static void span(buf *out, const uniscript_meta_run *run) {
	buf attributes = { 0 }, style = { 0 };
	str key = str_of(run->key), value = str_of(run->value), template;
	uniscript_font font;
	bool has_template = meta_template(key, &template);
	if (str_eq(key, FONT_KEY) && uniscript_font_lookup(run->value, &font)) {
		attribute(&attributes, LANG_KEY, str_of(font.lang));
		buf_addz(&style, "font-family: ");
		quoted(&style, font.families, font.family_count);
		if (font.feature_count) {
			buf_addz(&style, "; font-feature-settings: ");
			quoted(&style, font.features, font.feature_count);
		}
		uniscript_font_free(&font);
	} else if (str_eq(key, FONT_KEY) && has_template) {
		buf single = { 0 };
		buf_addf(&single, "'%s'", run->value);
		declaration(&style, template, buf_str(&single));
		buf_free(&single);
	} else if (str_eq(key, LANG_KEY)) {
		attribute(&attributes, LANG_KEY, value);
	} else if (has_template) {
		declaration(&style, template, value);
	} else {
		buf data_name = { 0 };
		buf_addf(&data_name, "data-%s", run->key);
		attribute(&attributes, data_name.p, value);
		buf_free(&data_name);
	}
	if (style.n) attribute(&attributes, "style", buf_str(&style));
	buf_addf(out, "<span%.*s>", S(buf_str(&attributes)));
	buf_free(&attributes);
	buf_free(&style);
}

/* The text with a span before each run and its close after it, the text escaped */
static void interleaved(buf *out, const uniscript_styled *styled) {
	str text = str_of(styled->text);
	size_t cursor = 0, depth = 0;
	const uniscript_meta_run **enclosing = malloc((styled->run_count + 1) * sizeof *enclosing);
	if (!enclosing) abort();
#define ADVANCE(to) (escape_html(out, str_slice(text, cursor, (to))), cursor = (to))
	for (size_t i = 0; i < styled->run_count; i++) {
		const uniscript_meta_run *run = &styled->runs[i];
		while (depth && enclosing[depth - 1]->end <= run->start) {
			depth--;
			ADVANCE(enclosing[depth]->end);
			buf_addz(out, CLOSE_SPAN);
		}
		ADVANCE(run->start);
		span(out, run);
		enclosing[depth++] = run;
	}
	while (depth) {
		depth--;
		ADVANCE(enclosing[depth]->end);
		buf_addz(out, CLOSE_SPAN);
	}
	ADVANCE(text.n);
#undef ADVANCE
	free(enclosing);
}

uniscript_result uniscript_html(const char *tagged) {
	if (invalid(tagged)) return failed(UNISCRIPT_INVALID_INPUT, NULL, 0);
	uniscript_styled styled = uniscript_meta_runs(tagged);
	buf out = { 0 };
	interleaved(&out, &styled);
	uniscript_result result = { .text = buf_take(&out), .warnings = styled.warnings, .warning_count = styled.warning_count };
	styled.warnings = NULL;
	styled.warning_count = 0;
	uniscript_styled_free(&styled);
	return result;
}

void uniscript_free(char *text) { free(text); }

void uniscript_result_free(uniscript_result *result) {
	if (!result) return;
	free(result->text);
	free(result->error);
	free(result->error_detail);
	free_warnings(result->warnings, result->warning_count);
	*result = (uniscript_result){ 0 };
}

void uniscript_styled_free(uniscript_styled *styled) {
	if (!styled) return;
	free(styled->text);
	for (size_t i = 0; i < styled->run_count; i++) {
		free(styled->runs[i].key);
		free(styled->runs[i].value);
	}
	free(styled->runs);
	free_warnings(styled->warnings, styled->warning_count);
	*styled = (uniscript_styled){ 0 };
}

static void free_list(char **items, size_t count) {
	for (size_t i = 0; i < count; i++) free(items[i]);
	free(items);
}

void uniscript_font_free(uniscript_font *font) {
	if (!font) return;
	free(font->name);
	free(font->lang);
	free_list(font->families, font->family_count);
	free_list(font->features, font->feature_count);
	*font = (uniscript_font){ 0 };
}
