/* Uniscript as a WebAssembly core module: uniscript_c.wasm (make wasm), this crate for wasm32-unknown-unknown, with
 * no imports. It exports these functions of ../uniscript.h over texts, plus malloc and free: a host copies a text into
 * a block of the module's malloc and frees the results with uniscript_free. Functions taking or returning structs are
 * left out (a WebAssembly host passes no structs); uniscript_error and uniscript_warnings tell what uniscript_convert
 * would. All strings are NUL-terminated UTF-8. A release asset since v1.0.8, called by warp's `use uniscript`. */
#ifndef UNISCRIPT_C_H
#define UNISCRIPT_C_H

#include <stddef.h>

/* Uniscript → Unicode; NULL on an error */
char *uniscript_to_unicode(const char *source);

/* The error converting the source gives ("unknown uniscript entity: x"), NULL when it converts */
char *uniscript_error(const char *source);

/* The warnings converting the source gives, one per line as "uniscript: <message> at byte N"; "" without any */
char *uniscript_warnings(const char *source);

/* Unicode → uniscript; uniscript_to_unicode gives the text back. NULL only for invalid UTF-8 */
char *uniscript_to_uniscript(const char *text);

/* Unicode → uniscript in ASCII only (\:U+E000 for a character without a name) */
char *uniscript_to_ascii_uniscript(const char *text);

/* The source with its opener-like inline tags in explicit form (<:alpha> → \:alpha) */
char *uniscript_explicit(const char *source);

/* The CSS declaration template of a meta key ("color" → "color: {}"), NULL if unknown */
char *uniscript_meta_template(const char *key);

void uniscript_free(char *text);

#endif
