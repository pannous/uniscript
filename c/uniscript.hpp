// Uniscript for C++17: header-only wrapper over the C API (c/uniscript.h) of c/ffi or c/native.
//
//   uniscript::to_unicode("<:alpha> <:fracture A>")           // "α 𝔄", throws uniscript::Error; warnings to stderr
//   uniscript::convert("<:greek q>")                          // {"q", {{"no greek form of q", 0}}}
//   uniscript::convert("<:greek q>", uniscript::Mode::Error)  // throws uniscript::Error, kind Unsupported
//   uniscript::to_uniscript("α 𝔄")                           // "\\:alpha \\:fracture-A"
//   uniscript::html(tagged)                                   // meta information as <span>s with CSS
#ifndef UNISCRIPT_HPP
#define UNISCRIPT_HPP

#include "uniscript.h"

#include <cstdio>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace uniscript {

inline constexpr const char *version = UNISCRIPT_VERSION;

enum class Mode { Warn = UNISCRIPT_WARN, Error = UNISCRIPT_ERROR, Lenient = UNISCRIPT_LENIENT };

enum class ErrorKind {
	UnknownEntity = UNISCRIPT_UNKNOWN_ENTITY,
	Unclosed = UNISCRIPT_UNCLOSED,
	Unsupported = UNISCRIPT_UNSUPPORTED,
	InvalidMeta = UNISCRIPT_INVALID_META,
	InvalidInput = UNISCRIPT_INVALID_INPUT,
};

struct Warning {
	std::string message;
	size_t at = 0;
	bool operator==(const Warning &other) const { return message == other.message && at == other.at; }
};

/// what(): the message of the Rust error; detail: the entity name, the rest after <:, the warning message, the tag
struct Error : std::runtime_error {
	ErrorKind kind;
	std::string detail;
	size_t at;
	Error(ErrorKind kind, const std::string &message, std::string detail, size_t at)
		: std::runtime_error(message), kind(kind), detail(std::move(detail)), at(at) {}
};

struct Conversion {
	std::string text;
	std::vector<Warning> warnings;
};

struct Header {
	std::string version; // "" when the header names none
	size_t length = 0;   // bytes of the header and the line break after it
};

struct MetaRun {
	std::string key, value;
	size_t start = 0, end = 0, at = 0;
};

struct Styled {
	std::string text;
	std::vector<MetaRun> runs;
	std::vector<Warning> warnings;
};

struct Font {
	std::string name, lang;
	std::vector<std::string> families, features;
};

namespace detail {

inline std::string take(char *text) {
	std::unique_ptr<char, decltype(&uniscript_free)> owner(text, &uniscript_free);
	return text ? std::string(text) : std::string();
}

inline std::optional<std::string> take_optional(char *text) {
	if (!text) return std::nullopt;
	return take(text);
}

inline std::vector<Warning> warnings(const uniscript_warning *warnings, size_t count) {
	std::vector<Warning> out;
	for (size_t i = 0; i < count; i++) out.push_back({warnings[i].message, warnings[i].at});
	return out;
}

inline std::vector<std::string> strings(char *const *items, size_t count) { return {items, items + count}; }

template <typename T, void (*release)(T *)>
struct Owned : T {
	explicit Owned(T value) : T(value) {}
	Owned(const Owned &) = delete;
	Owned &operator=(const Owned &) = delete;
	~Owned() { release(this); }
};

/// The text and warnings of a C result, or its error thrown
inline Conversion unwrap(uniscript_result result) {
	Owned<uniscript_result, uniscript_result_free> owned(result);
	if (owned.error_kind != UNISCRIPT_OK)
		throw Error(static_cast<ErrorKind>(owned.error_kind), owned.error, owned.error_detail, owned.error_at);
	return {owned.text, warnings(owned.warnings, owned.warning_count)};
}

} // namespace detail

/// Uniscript → Unicode (meta information as TAG sequences) and its warnings; in Mode::Error the first warning is the error
inline Conversion convert(const std::string &source, Mode mode = Mode::Warn) {
	return detail::unwrap(uniscript_convert(source.c_str(), static_cast<uniscript_mode>(mode)));
}

/// Uniscript → Unicode; warnings go to stderr
inline std::string to_unicode(const std::string &source) {
	Conversion conversion = convert(source);
	for (const Warning &warning : conversion.warnings)
		std::fprintf(stderr, "warning: uniscript: %s at byte %zu\n", warning.message.c_str(), warning.at);
	return conversion.text;
}

/// Unicode → uniscript; to_unicode gives the text back
inline std::string to_uniscript(const std::string &text) {
	char *spelled = uniscript_to_uniscript(text.c_str());
	if (!spelled) throw Error(ErrorKind::InvalidInput, "uniscript: invalid input (not UTF-8)", "", 0);
	return detail::take(spelled);
}

/// Unicode → uniscript in ASCII only: a character without a name is written by its code point (\:U+E000)
inline std::string to_ascii_uniscript(const std::string &text) {
	char *spelled = uniscript_to_ascii_uniscript(text.c_str());
	if (!spelled) throw Error(ErrorKind::InvalidInput, "uniscript: invalid input (not UTF-8)", "", 0);
	return detail::take(spelled);
}

/// The source with its opener-like inline tags in explicit form (<:alpha> → \:alpha); `explicit` is a C++ keyword
inline std::string explicit_tags(const std::string &source) {
	char *rewritten = uniscript_explicit(source.c_str());
	if (!rewritten) throw Error(ErrorKind::InvalidInput, "uniscript: invalid input (not UTF-8)", "", 0);
	return detail::take(rewritten);
}

/// The header <:uniscript version="…"> at the start of the source; it is no header anywhere else
inline std::optional<Header> header(const std::string &source) {
	const char *version = nullptr;
	size_t version_length = 0, length = 0;
	if (!uniscript_header(source.c_str(), &version, &version_length, &length)) return std::nullopt;
	return Header{std::string(version, version_length), length};
}

/// Tagged text → plain text, nested meta runs and warnings (unknown keys, unmatched closes)
inline Styled meta_runs(const std::string &tagged) {
	detail::Owned<uniscript_styled, uniscript_styled_free> styled(uniscript_meta_runs(tagged.c_str()));
	Styled out{styled.text, {}, detail::warnings(styled.warnings, styled.warning_count)};
	for (size_t i = 0; i < styled.run_count; i++) {
		const uniscript_meta_run &run = styled.runs[i];
		out.runs.push_back({run.key, run.value, run.start, run.end, run.at});
	}
	return out;
}

/// HTML of tagged text (each meta run a <span> with its lang and CSS) and the warnings of meta_runs
inline Conversion html(const std::string &tagged) { return detail::unwrap(uniscript_html(tagged.c_str())); }

/// A font style of the entities: cuneiform-hittite, han-japanese
inline std::optional<Font> font(const std::string &name) {
	uniscript_font found{};
	if (!uniscript_font_lookup(name.c_str(), &found)) return std::nullopt;
	detail::Owned<uniscript_font, uniscript_font_free> owned(found);
	return Font{owned.name, owned.lang, detail::strings(owned.families, owned.family_count),
	            detail::strings(owned.features, owned.feature_count)};
}

/// The CSS declaration template of a meta key (color → "color: {}")
inline std::optional<std::string> meta_template(const std::string &key) {
	return detail::take_optional(uniscript_meta_template(key.c_str()));
}

} // namespace uniscript

#endif
