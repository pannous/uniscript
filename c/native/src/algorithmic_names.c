/* Unicode names that are no entries of the index but derived from the code point (UAX #44 rules NR1 and NR2):
 * `CJK UNIFIED IDEOGRAPH-4E00` is 一, `HANGUL SYLLABLE GA` is 가, `TANGUT COMPONENT-001` is U+18800. Matched in any case,
 * hyphens as spaces, as the case fallback of tag() reads names (port of src/algorithmic_names.rs). */
#include <string.h>

#include "internal.h"

#define COUNT(array) (sizeof(array) / sizeof((array)[0]))
#define MIN_HEX_DIGITS 4
#define MAX_HEX_DIGITS 8
#define MAX_DECIMAL_DIGITS 9
#define MAX_NAME 64

typedef struct { uint32_t first, last; } range;

static const range CJK_UNIFIED[] = {
	{ 0x3400, 0x4DBF }, { 0x4E00, 0x9FFF }, { 0x20000, 0x2A6DF }, { 0x2A700, 0x2B73F }, { 0x2B740, 0x2B81F }, { 0x2B820, 0x2CEAF },
	{ 0x2CEB0, 0x2EBEF }, { 0x2EBF0, 0x2EE5F }, { 0x30000, 0x3134F }, { 0x31350, 0x323AF },
};
static const range CJK_COMPATIBILITY[] = { { 0xF900, 0xFAFF }, { 0x2F800, 0x2FA1F } };
static const range TANGUT[] = { { 0x17000, 0x187FF }, { 0x18D00, 0x18D7F } };
static const range KHITAN[] = { { 0x18B00, 0x18CFF } };
static const range NUSHU[] = { { 0x1B170, 0x1B2FF } };
static const range EGYPTIAN[] = { { 0x13460, 0x143FF } };

/* NR2: name prefix → the ranges whose characters are named by it and their code point in hex (Unicode 16.0.0 blocks) */
static const struct { const char *prefix; const range *ranges; size_t count; } HEX_NAMED[] = {
	{ "CJK UNIFIED IDEOGRAPH ", CJK_UNIFIED, COUNT(CJK_UNIFIED) },
	{ "CJK COMPATIBILITY IDEOGRAPH ", CJK_COMPATIBILITY, COUNT(CJK_COMPATIBILITY) },
	{ "TANGUT IDEOGRAPH ", TANGUT, COUNT(TANGUT) },
	{ "KHITAN SMALL SCRIPT CHARACTER ", KHITAN, COUNT(KHITAN) },
	{ "NUSHU CHARACTER ", NUSHU, COUNT(NUSHU) },
	{ "EGYPTIAN HIEROGLYPH ", EGYPTIAN, COUNT(EGYPTIAN) },
};
/* `TANGUT COMPONENT-001` is the first of the Tangut Components block, numbered in decimal */
static const char TANGUT_COMPONENT[] = "TANGUT COMPONENT ";
static const range TANGUT_COMPONENTS = { 0x18800, 0x18AFF };
static const char HANGUL_SYLLABLE[] = "HANGUL SYLLABLE ";
#define HANGUL_BASE 0xAC00
/* NR1: the jamo short names of a syllable's leading consonant, vowel and trailing consonant */
static const char *const LEADING[] = { "G", "GG", "N", "D", "DD", "R", "M", "B", "BB", "S", "SS", "", "J", "JJ", "C", "K", "T", "P", "H" };
static const char *const VOWELS[] = { "A", "AE", "YA", "YAE", "EO", "E", "YEO", "YE", "O", "WA", "WAE", "OE", "YO", "U", "WEO", "WE",
	"WI", "YU", "EU", "YI", "I" };
static const char *const TRAILING[] = { "", "G", "GG", "GS", "N", "NJ", "NH", "D", "L", "LG", "LM", "LB", "LS", "LT", "LP", "LH", "M",
	"B", "BS", "S", "SS", "NG", "J", "C", "K", "T", "P", "H" };

static bool within(uint32_t code_point, const range *ranges, size_t count, uint32_t *character) {
	for (size_t i = 0; i < count; i++) {
		if (code_point >= ranges[i].first && code_point <= ranges[i].last) {
			*character = code_point;
			return true;
		}
	}
	return false;
}

/* the value of the digits in the base, false for an empty, too long or foreign digit */
static bool number(str digits, uint32_t base, size_t max_digits, uint32_t *value) {
	if (!digits.n || digits.n > max_digits) return false;
	*value = 0;
	for (size_t i = 0; i < digits.n; i++) {
		char c = digits.p[i];
		uint32_t digit = c >= '0' && c <= '9' ? (uint32_t)(c - '0') : c >= 'A' && c <= 'F' ? (uint32_t)(c - 'A' + 10) : base;
		if (digit >= base) return false;
		*value = *value * base + digit;
	}
	return true;
}

/* The syllable whose short names spell `name`: `GA` is 가, `HIH` is 힣; the first syllable of a spelling wins */
static bool hangul_syllable(str name, uint32_t *character) {
	uint32_t index = 0;
	for (size_t leading = 0; leading < COUNT(LEADING); leading++)
		for (size_t vowel = 0; vowel < COUNT(VOWELS); vowel++)
			for (size_t trailing = 0; trailing < COUNT(TRAILING); trailing++, index++) {
				size_t l = strlen(LEADING[leading]), v = strlen(VOWELS[vowel]), t = strlen(TRAILING[trailing]);
				if (l + v + t == name.n && !memcmp(name.p, LEADING[leading], l) && !memcmp(name.p + l, VOWELS[vowel], v) &&
				    !memcmp(name.p + l + v, TRAILING[trailing], t)) {
					*character = HANGUL_BASE + index;
					return true;
				}
			}
	return false;
}

bool algorithmic_character(str name, uint32_t *character) {
	if (name.n > MAX_NAME) return false;
	char upper[MAX_NAME];
	for (size_t i = 0; i < name.n; i++) {
		char c = name.p[i];
		upper[i] = c >= 'a' && c <= 'z' ? (char)(c - 'a' + 'A') : c == '-' ? ' ' : c;
	}
	str spelled = { upper, name.n };
	uint32_t value;
	if (str_starts(spelled, HANGUL_SYLLABLE)) return hangul_syllable(str_from(spelled, strlen(HANGUL_SYLLABLE)), character);
	if (str_starts(spelled, TANGUT_COMPONENT)) {
		return number(str_from(spelled, strlen(TANGUT_COMPONENT)), 10, MAX_DECIMAL_DIGITS, &value) && value > 0 &&
		       within(TANGUT_COMPONENTS.first + value - 1, &TANGUT_COMPONENTS, 1, character);
	}
	for (size_t i = 0; i < COUNT(HEX_NAMED); i++) {
		if (!str_starts(spelled, HEX_NAMED[i].prefix)) continue;
		str digits = str_from(spelled, strlen(HEX_NAMED[i].prefix));
		return digits.n >= MIN_HEX_DIGITS && number(digits, 16, MAX_HEX_DIGITS, &value) &&
		       within(value, HEX_NAMED[i].ranges, HEX_NAMED[i].count, character);
	}
	return false;
}
