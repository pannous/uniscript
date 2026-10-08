#include <cassert>
#include <iostream>
#include "uniscript.hpp"

int main() {
	// round trip; to_unicode prints warnings to stderr and throws uniscript::Error
	assert(uniscript::to_unicode("<:alpha> <:fracture A>") == "α 𝔄");
	assert(uniscript::to_uniscript("α 𝔄") == "\\:alpha \\:fracture-A");

	// every tag form
	for (auto [source, unicode] : {std::pair{"\\:alpha", "α"}, {"<:greek small letter alpha>", "α"}, {"<:double-R>", "ℝ"},
	                               {"<:bold italic alpha>", "𝜶"}, {"<:greek>athos<:/greek>", "αθος"}, {"<:greek>athos<:>", "αθος"},
	                               {"<<::>alpha>", "<:alpha>"}, {"\\:U+1F60D <:0x1F60D> \\U1F60D", "😍 😍 😍"},
	                               {"\\:1F60D", "😍"}, {"\\:bed", "🛏"}})
		assert(uniscript::to_unicode(source) == unicode);

	// warnings and the modes Warn (default), Error and Lenient
	auto [text, warnings] = uniscript::convert("<:fracture 7>");
	assert(text == "7" && warnings.at(0).message == "no fracture form of 7");
	try {
		uniscript::convert("<:fracture 7>", uniscript::Mode::Error);
		assert(!"Mode::Error throws");
	} catch (const uniscript::Error &error) {
		assert(error.kind == uniscript::ErrorKind::Unsupported);
	}
	try {
		uniscript::convert("<:nosuch>");
		assert(!"an unknown name throws");
	} catch (const uniscript::Error &error) {
		assert(error.kind == uniscript::ErrorKind::UnknownEntity && error.detail == "nosuch");
	}
	assert(uniscript::convert("<:nosuch>", uniscript::Mode::Lenient).text == "<:nosuch>");

	// the header
	const std::string source = "<:uniscript version=\"https://uniscript.org/v1\">\n\\:alpha";
	assert(uniscript::header(source)->version == uniscript::version);
	assert(uniscript::to_unicode(source) == "α");

	// meta information
	const std::string tagged = uniscript::convert("<:color red 𓀀>").text;
	auto styled = uniscript::meta_runs(tagged);
	assert(styled.text == "𓀀" && styled.runs.at(0).key == "color" && styled.runs.at(0).value == "red");
	assert(uniscript::html(tagged).text == "<span style=\"color: red\">𓀀</span>");
	std::cout << "c++: ok" << std::endl;
}
