/* The binary index data/entities.idx (format in AGENTS.md), compiled into the library with .incbin: tables of
 * 20-byte records sorted by (hash, key), then a string pool */
#include "internal.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef UNISCRIPT_INDEX_PATH
#error "define UNISCRIPT_INDEX_PATH, the path of data/entities.idx"
#endif

#define HASH_MULTIPLIER 31u
#define RECORD_SIZE 20
#define HEADER_FIXED 8
#define TABLE_ENTRY_SIZE 8

#if defined(__APPLE__)
#define INDEX_SECTION ".const"
#define SYMBOL(name) "_" #name
#else
#define INDEX_SECTION ".section .rodata"
#define SYMBOL(name) #name
#endif

__asm__(INDEX_SECTION "\n"
	".balign 4\n"
	".globl " SYMBOL(uniscript_index_start) "\n" SYMBOL(uniscript_index_start) ":\n"
	".incbin \"" UNISCRIPT_INDEX_PATH "\"\n"
	".globl " SYMBOL(uniscript_index_end) "\n" SYMBOL(uniscript_index_end) ":\n"
	".previous\n");
extern const unsigned char uniscript_index_start[], uniscript_index_end[];

static uint32_t u32_at(size_t offset) {
	const unsigned char *b = uniscript_index_start + offset;
	return (uint32_t)b[0] | (uint32_t)b[1] << 8 | (uint32_t)b[2] << 16 | (uint32_t)b[3] << 24;
}

static size_t index_size(void) { return (size_t)(uniscript_index_end - uniscript_index_start); }

bool index_valid(void) {
	return index_size() >= HEADER_FIXED && memcmp(uniscript_index_start, "USX1", 4) == 0 && u32_at(4) >= TABLE_COUNT;
}

uint32_t text_hash(str text) {
	uint32_t hash = 0;
	for (size_t i = 0; i < text.n; i++) hash = hash * HASH_MULTIPLIER + (unsigned char)text.p[i];
	return hash;
}

static size_t table_records(table in) { return u32_at(HEADER_FIXED + TABLE_ENTRY_SIZE * in); }

size_t index_count(table in) { return u32_at(HEADER_FIXED + TABLE_ENTRY_SIZE * in + 4); }

static str pool_text(size_t field_offset) {
	return (str){ (const char *)uniscript_index_start + u32_at(field_offset), u32_at(field_offset + 4) };
}

void index_record(table in, size_t position, uint32_t *hash, str *key, str *value) {
	size_t at = table_records(in) + position * RECORD_SIZE;
	*hash = u32_at(at);
	*key = pool_text(at + 4);
	*value = pool_text(at + 12);
}

/* Binary search for the first record of the key's hash, then compare keys (hashes may collide) */
bool index_entry(table in, str key, str *stored_key, str *value) {
	uint32_t wanted = text_hash(key);
	size_t count = index_count(in), low = 0, high = count;
	while (low < high) {
		size_t middle = (low + high) / 2;
		if (u32_at(table_records(in) + middle * RECORD_SIZE) < wanted)
			low = middle + 1;
		else
			high = middle;
	}
	for (size_t position = low; position < count; position++) {
		uint32_t hash;
		str record_key, record_value;
		index_record(in, position, &hash, &record_key, &record_value);
		if (hash != wanted) break;
		if (record_key.n == key.n && memcmp(record_key.p, key.p, key.n) == 0) {
			if (stored_key) *stored_key = record_key;
			*value = record_value;
			return true;
		}
	}
	return false;
}

bool index_get(table in, str key, str *value) {
	str ignored;
	return index_entry(in, key, NULL, value ? value : &ignored);
}

bool index_getf(table in, str *value, const char *format, ...) {
	char small[256];
	va_list arguments, again;
	va_start(arguments, format);
	va_copy(again, arguments);
	int n = vsnprintf(small, sizeof small, format, arguments);
	va_end(arguments);
	char *key = small;
	if ((size_t)n >= sizeof small) {
		key = malloc((size_t)n + 1);
		if (!key) abort();
		vsnprintf(key, (size_t)n + 1, format, again);
	}
	va_end(again);
	bool found = index_get(in, (str){ key, (size_t)n }, value);
	if (key != small) free(key);
	return found;
}
