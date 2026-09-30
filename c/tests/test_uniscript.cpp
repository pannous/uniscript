// The reference cases (cases.h) through the C++17 wrapper uniscript.hpp; links against c/ffi or c/native
#include "../uniscript.hpp"
#include "cases.h"

#include <functional>
#include <iostream>

namespace {

int checks, failures;

void check(bool passed, const std::string &what, const std::string &input, const std::string &got, const std::string &expected) {
	checks++;
	if (passed) return;
	failures++;
	std::cout << "FAIL " << what << ": " << input << "\n  got      " << got << "\n  expected " << expected << "\n";
}

template <typename T>
void check_equal(const std::string &what, const std::string &input, const T &got, const T &expected) {
	if constexpr (std::is_same_v<T, std::string>) check(got == expected, what, input, got, expected);
	else check(got == expected, what, input, std::to_string(got), std::to_string(expected));
}

std::string expanded(const char *text) {
	char *expansion = expand_tags(text);
	std::string out(expansion);
	free(expansion);
	return out;
}

std::string messages(const std::vector<uniscript::Warning> &warnings) {
	std::string out;
	for (const auto &warning : warnings) out += warning.message + "@" + std::to_string(warning.at) + "; ";
	return out;
}

/// The error the call throws, or a failed check
std::optional<uniscript::Error> thrown(const std::string &input, const std::function<void()> &call) {
	try {
		call();
	} catch (const uniscript::Error &error) {
		return error;
	}
	check(false, "throws", input, "no error", "uniscript::Error");
	return std::nullopt;
}

void test_converts(const conversion_case &c) {
	auto conversion = uniscript::convert(expanded(c.uniscript));
	check_equal("convert", c.uniscript, conversion.text, expanded(c.unicode));
	check_equal("warnings", c.uniscript, messages(conversion.warnings), std::string());
}

void test_spells(const conversion_case &c) {
	check_equal("to_uniscript", c.unicode, uniscript::to_uniscript(expanded(c.unicode)), std::string(c.uniscript));
}

void test_restores(const char *text) {
	std::string unicode = expanded(text);
	check_equal("round trip", text, uniscript::to_unicode(uniscript::to_uniscript(unicode)), unicode);
}

void test_warns(const warning_case &c) {
	auto conversion = uniscript::convert(c.uniscript, uniscript::Mode::Warn);
	check_equal("warned text", c.uniscript, conversion.text, expanded(c.unicode));
	check(conversion.warnings == std::vector<uniscript::Warning>{{c.message, c.at}}, "warnings", c.uniscript,
	      messages(conversion.warnings), c.message);
	auto error = thrown(c.uniscript, [&] { uniscript::convert(c.uniscript, uniscript::Mode::Error); });
	if (!error) return;
	check(error->kind == uniscript::ErrorKind::Unsupported, "error kind", c.uniscript, error->what(), "Unsupported");
	check_equal("error detail", c.uniscript, error->detail, std::string(c.message));
	check_equal("error at", c.uniscript, error->at, c.at);
}

void test_fails(const error_case &c) {
	auto error = thrown(c.uniscript, [&] { uniscript::to_unicode(c.uniscript); });
	if (!error) return;
	check_equal("error kind", c.uniscript, static_cast<int>(error->kind), c.kind);
	check_equal("error detail", c.uniscript, error->detail, std::string(c.detail));
	check_equal("error", c.uniscript, std::string(error->what()), std::string(c.error));
}

void test_lenient(const lenient_case &c) {
	auto conversion = uniscript::convert(c.uniscript, uniscript::Mode::Lenient);
	check_equal("lenient", c.uniscript, conversion.text, std::string(c.unicode));
	std::vector<std::string> got, expected;
	for (const auto &warning : conversion.warnings) got.push_back(warning.message);
	for (const char *message : c.messages)
		if (message) expected.push_back(message);
	check(got == expected, "lenient warnings", c.uniscript, messages(conversion.warnings), expected.empty() ? "" : expected[0]);
}

void test_finds_header(const header_case &c) {
	auto header = uniscript::header(c.source);
	check_equal("header found", c.source, header.has_value(), static_cast<bool>(c.found));
	if (!header) return;
	check_equal("header version", c.source, header->version, std::string(c.version));
	check_equal("header length", c.source, header->length, c.length);
}

void test_renders(const html_case &c) {
	auto rendered = uniscript::html(expanded(c.tagged));
	std::string html = expanded(c.html);
	bool passed = c.contains ? rendered.text.find(html) != std::string::npos : rendered.text == html;
	check(passed, "html", c.tagged, rendered.text, html);
	std::vector<uniscript::Warning> expected;
	if (c.message) expected.push_back({c.message, c.at});
	check(rendered.warnings == expected, "html warnings", c.tagged, messages(rendered.warnings), messages(expected));
}

void test_finds_font(const font_case &c) {
	auto font = uniscript::font(c.name);
	check_equal("font found", c.name, font.has_value(), c.lang != nullptr);
	if (!font) return;
	check_equal("font lang", c.name, font->lang, std::string(c.lang));
	if (c.first_family) check_equal("font family", c.name, font->families.empty() ? "" : font->families[0], std::string(c.first_family));
	if (c.first_feature) check_equal("font feature", c.name, font->features.empty() ? "" : font->features[0], std::string(c.first_feature));
}

void meta_runs_nest() {
	std::string tagged = expanded("x{<font cuneiform-hittite}𒀭A{:color red}{</font}");
	auto styled = uniscript::meta_runs(tagged);
	check_equal("styled text", tagged, styled.text, std::string("x𒀭A"));
	check_equal("runs", tagged, styled.runs.size(), size_t{2});
	if (styled.runs.size() != 2) return;
	check_equal("run", tagged, styled.runs[0].key + " " + styled.runs[0].value, std::string("font cuneiform-hittite"));
	check_equal("run range", tagged, std::to_string(styled.runs[0].start) + "-" + std::to_string(styled.runs[0].end), std::string("1-6"));
	check_equal("attached", tagged, styled.runs[1].key + "@" + std::to_string(styled.runs[1].start), std::string("color@5"));
}

void edges() {
	check_equal("meta template", "color", uniscript::meta_template("color").value_or("none"), std::string("color: {}"));
	check_equal("no meta template", "blink", uniscript::meta_template("blink").has_value(), false);
	auto error = thrown("\\xff", [] { uniscript::convert("\xff<:alpha>", uniscript::Mode::Lenient); });
	if (error) check(error->kind == uniscript::ErrorKind::InvalidInput, "invalid UTF-8", "\\xff", error->what(), "InvalidInput");
	check_equal("version", "version", std::string(uniscript::version), std::string("https://uniscript.org/v1"));
	check(uniscript::to_uniscript(expanded(SCOTLAND)).find("green") == std::string::npos, "no green suffix", SCOTLAND, "", "");
}

template <typename Table, typename Test>
void each(const Table &table, Test test) {
	for (const auto &item : table) test(item);
}

} // namespace

int main() {
	each(round_trips, test_converts);
	each(round_trips, test_spells);
	each(converts, test_converts);
	each(spells_back, test_spells);
	each(restores, test_restores);
	each(warns, test_warns);
	each(errors, test_fails);
	each(lenients, test_lenient);
	each(headers, test_finds_header);
	each(htmls, test_renders);
	each(fonts, test_finds_font);
	meta_runs_nest();
	edges();
	std::cout << "C++: " << checks << " checks, " << failures << " failures\n";
	return failures != 0;
}
