/* Uniscript C API: ASCII names for Unicode text (<:alpha> → α, <:fracture A> → 𝔄) and back.
 *
 * One header for both C libraries: c/ffi (wraps the Rust crate) and c/native (plain C), drop-in interchangeable.
 * The built-in index data/entities.idx is compiled in. All strings are NUL-terminated UTF-8. Strings and structs the
 * library returns are malloc'ed by it: free a char * with uniscript_free, a struct with its *_free function (both
 * accept NULL). Offsets (at, start, end, length) are byte offsets. Conversion never stops on errors in
 * UNISCRIPT_LENIENT: faulty uniscript stays as written, with a warning. */
#ifndef UNISCRIPT_H
#define UNISCRIPT_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* The current uniscript version of the header <:uniscript version="…">; every https://uniscript.org/vN is read
 * without warning, a foreign version URL warns */
#define UNISCRIPT_VERSION "https://uniscript.org/v1"

/* Whether unsupported characters are warnings (the output keeps them plain) or errors; LENIENT also turns errors
 * (unknown entities, invalid meta values, an unclosed <:) into warnings and keeps their uniscript as written */
typedef enum { UNISCRIPT_WARN, UNISCRIPT_ERROR, UNISCRIPT_LENIENT } uniscript_mode;

typedef enum {
	UNISCRIPT_OK,
	UNISCRIPT_UNKNOWN_ENTITY, /* detail: the name */
	UNISCRIPT_UNCLOSED,       /* detail: the rest of the text from <: */
	UNISCRIPT_UNSUPPORTED,    /* a warning in UNISCRIPT_ERROR mode; detail: its message, error_at: its offset */
	UNISCRIPT_INVALID_META,   /* detail: the tag content */
	UNISCRIPT_INVALID_INPUT   /* NULL or invalid UTF-8, except in uniscript_convert with UNISCRIPT_LENIENT */
} uniscript_error_kind;

/* A character or combination without a Unicode counterpart; message without the "uniscript: " prefix */
typedef struct {
	char *message;
	size_t at;
} uniscript_warning;

typedef struct {
	char *text;                     /* NULL on error */
	uniscript_error_kind error_kind;
	char *error;                    /* NULL on success: "unknown uniscript entity: x", "unclosed <: at …",
	                                   "uniscript: <message> at byte N", "invalid meta value in <:…>" */
	char *error_detail;             /* NULL on success */
	size_t error_at;                /* the warning's offset for UNISCRIPT_UNSUPPORTED, else 0 */
	uniscript_warning *warnings;
	size_t warning_count;
} uniscript_result;

/* A byte range of the plain text under one meta key; at: offset of its sequence in the tagged text */
typedef struct {
	char *key;
	char *value;
	size_t start, end, at;
} uniscript_meta_run;

/* Plain text without its meta sequences, the runs they cover (nested, in opening order) and the warnings */
typedef struct {
	char *text;
	uniscript_meta_run *runs;
	size_t run_count;
	uniscript_warning *warnings;
	size_t warning_count;
} uniscript_styled;

/* A font style of the entities: the value of <:font cuneiform-hittite> */
typedef struct {
	char *name;
	char *lang;                     /* BCP 47: hit-Xsux, ja */
	char **families;                /* CSS font-family fallback list */
	size_t family_count;
	char **features;                /* OpenType feature tags */
	size_t feature_count;
} uniscript_font;

/* Uniscript → Unicode (meta information as TAG sequences) and its warnings; in UNISCRIPT_ERROR the first warning is
 * the error. In UNISCRIPT_LENIENT invalid input is repaired instead of failing: each maximal invalid UTF-8 subpart
 * becomes U+FFFD with the warning "invalid UTF-8 byte 0xNN replaced by U+FFFD" at its offset in the input (as Rust's
 * String::from_utf8_lossy), NULL is "" with the warning "input is NULL"; these warnings come first, the conversion's
 * follow at offsets of the repaired text */
uniscript_result uniscript_convert(const char *source, uniscript_mode mode);

/* Uniscript → Unicode; NULL on an error, warnings go to stderr as "warning: uniscript: <message> at byte <n>\n" */
char *uniscript_to_unicode(const char *source);

/* Unicode → uniscript; uniscript_to_unicode gives the text back. NULL only for NULL or invalid UTF-8 */
char *uniscript_to_uniscript(const char *text);

/* The source with its opener-like inline tags in explicit form (<:alpha> → \:alpha, <:color red A> → <:color red A/>),
 * which converts alike without warnings; the header and everything else stay. NULL only for NULL or invalid UTF-8 */
char *uniscript_explicit(const char *source);

/* 1 if the source starts with the header <:uniscript …>: version points into the source (version_length bytes, 0
 * when it names none), length: bytes of the header and the line break after it. 0 otherwise. Out pointers may be
 * NULL. */
int uniscript_header(const char *source, const char **version, size_t *version_length, size_t *length);

/* Tagged text → plain text and meta runs; unknown keys and unmatched closes warn */
uniscript_styled uniscript_meta_runs(const char *tagged);

/* HTML of tagged text: each meta run a <span> with its lang and CSS. text: the HTML, warnings: those of
 * uniscript_meta_runs; an error only for invalid input */
uniscript_result uniscript_html(const char *tagged);

/* 1 and *font filled if the entities have that font style, else 0 */
int uniscript_font_lookup(const char *name, uniscript_font *font);

/* The CSS declaration template of a meta key ("color" → "color: {}"), NULL if unknown, NULL or invalid UTF-8 */
char *uniscript_meta_template(const char *key);

void uniscript_free(char *text);
void uniscript_result_free(uniscript_result *result);
void uniscript_styled_free(uniscript_styled *styled);
void uniscript_font_free(uniscript_font *font);

#ifdef __cplusplus
}
#endif

#endif
