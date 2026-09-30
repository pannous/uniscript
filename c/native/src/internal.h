/* Internals of the native C uniscript: text slices and buffers, UTF-8, the index reader, meta sequences */
#ifndef UNISCRIPT_INTERNAL_H
#define UNISCRIPT_INTERNAL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* A borrowed byte range, not NUL-terminated */
typedef struct { const char *p; size_t n; } str;
/* A growable, always NUL-terminated byte buffer */
typedef struct { char *p; size_t n, cap; } buf;

#define S(text) (int)(text).n, (text).p /* for printf's %.*s */
#define NO_CHARACTER UINT32_MAX

str str_of(const char *text);
str str_from(str text, size_t start);
str str_slice(str text, size_t start, size_t end);
bool str_eq(str text, const char *other);
bool str_starts(str text, const char *prefix);
/* position of the first byte, or text.n */
size_t str_find(str text, char byte);
bool split_once(str text, char separator, str *before, str *after);
bool is_whitespace(uint32_t character);
str trim_start(str text);
str trim(str text);

void buf_add(buf *out, const char *bytes, size_t n);
void buf_adds(buf *out, str text);
void buf_addz(buf *out, const char *text);
void buf_addc(buf *out, uint32_t character);
void buf_addf(buf *out, const char *format, ...);
str buf_str(const buf *text);
/* the buffer's text, owned by the caller; the buffer is empty afterwards */
char *buf_take(buf *text);
void buf_free(buf *text);
char *copy_of(str text);

/* the character at the start and its byte length (0 at the end); the text is valid UTF-8 */
size_t utf8_decode(str text, uint32_t *character);
size_t utf8_encode(uint32_t character, char out[5]);
bool utf8_valid(const char *text, size_t n);
/* whether a well-formed sequence starts the bytes; *length: its length or that of the maximal invalid subpart */
bool utf8_sequence(const char *text, size_t n, size_t *length);
uint32_t first_character(str text);

typedef enum { TABLE_NAMES, TABLE_CHARS, TABLE_SUFFIXES, TABLE_FONTS, TABLE_META, TABLE_COUNT } table;
uint32_t text_hash(str text);
/* the value of the key, and the stored key when wanted */
bool index_entry(table in, str key, str *stored_key, str *value);
bool index_get(table in, str key, str *value);
bool index_getf(table in, str *value, const char *format, ...);
bool index_valid(void);
size_t index_count(table in);
/* the key and value of a record in table order */
void index_record(table in, size_t position, uint32_t *hash, str *key, str *value);

/* meta sequences: sigil '<' opens, "</" closes, ':' attaches to the character before */
typedef enum { META_OPEN, META_CLOSE, META_ATTACHED } meta_kind;
/* key and value point into spelled, the ASCII the TAG characters spell */
typedef struct { meta_kind kind; buf spelled; str key, value; } meta;
#define CANCEL_TAG 0xE007Fu
void meta_tags(buf *out, meta_kind kind, str key, str value);
/* the uniscript of a span sequence (<:font x>, <:/font>); of an attached one "key value" */
void meta_uniscript(buf *out, const meta *sequence);
/* a meta sequence at the start of the text and its byte length, 0 if none; free a found one with meta_free */
size_t meta_at(str text, meta *found);
void meta_free(meta *sequence);
/* the byte length of an emoji tag sequence (TAG g b s c t CANCEL TAG after 🏴), 0 if none */
size_t emoji_tags_at(str text);
bool is_meta_value(str value);
bool extends(uint32_t previous, uint32_t character);
/* the text with the sequences after each character (with its marks and controls) */
void meta_attach(buf *out, str text, str sequences);
void escape_html(buf *out, str text);

#endif
