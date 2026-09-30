// A program built against an installed uniscript (make consumer-test): c++ -std=c++17 consumer.cpp $(pkg-config --cflags --libs uniscript)
#include <iostream>
#include <uniscript.hpp>

int main() {
	std::string text = uniscript::to_unicode("<:alpha> <:fracture A>");
	std::string spelled = uniscript::to_uniscript(text);
	bool ok = text == "α 𝔄" && spelled == "<:alpha> <:fracture A>";
	std::cout << (ok ? "ok   " : "FAIL ") << "C++ consumer: " << text << " | " << spelled << "\n";
	return !ok;
}
