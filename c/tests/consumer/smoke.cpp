// scripts/publish.sh's smoke test of an installed package: prints "<unicode> | <uniscript>" of its argument
#include <iostream>
#include <uniscript.hpp>

int main(int argc, char **argv) {
	if (argc != 2) return std::cerr << "usage: smoke <uniscript>\n", 2;
	std::string text = uniscript::to_unicode(argv[1]);
	std::cout << text << " | " << uniscript::to_uniscript(text) << "\n";
}
