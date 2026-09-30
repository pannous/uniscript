# Homebrew formula for the tap pannous/homebrew-tap (brew install pannous/tap/libuniscript): the native C11 library
# (c/native) with uniscript.h, the C++17 wrapper uniscript.hpp and uniscript.pc, from the tarball `make -C c/native dist`
# attached to the GitHub release. At a release: sha256 printed by make dist, see notes/c-packaging.md
class Libuniscript < Formula
  desc "C/C++ library: ASCII names for Unicode text (<:alpha> → α) and back"
  homepage "https://pannous.com/uniscript/"
  url "https://github.com/pannous/uniscript/releases/download/v0.2.0/uniscript-c-0.2.0.tar.gz"
  sha256 "REPLACE_WITH_SHA256_PRINTED_BY_MAKE_DIST"
  license "MIT"
  head "https://github.com/pannous/uniscript.git", branch: "main"

  depends_on "pkgconf" => :test

  def install
    # the command line `uniscript` comes from the formula uniscript (Rust), so only the library here
    system "make", "-C", "c/native", "install-lib", "PREFIX=#{prefix}"
  end

  test do
    (testpath/"test.c").write <<~C
      #include <string.h>
      #include <uniscript.h>
      int main(void) {
        char *text = uniscript_to_unicode("<:alpha> <:fracture A>");
        int ok = text && strcmp(text, "α 𝔄") == 0;
        uniscript_free(text);
        return !ok;
      }
    C
    (testpath/"test.cpp").write <<~CPP
      #include <uniscript.hpp>
      int main() { return uniscript::to_uniscript(uniscript::to_unicode("<:alpha> <:fracture A>")) != "<:alpha> <:fracture A>"; }
    CPP
    flags = shell_output("pkgconf --cflags --libs #{lib}/pkgconfig/uniscript.pc").split
    system ENV.cc, "-std=c11", "test.c", *flags, "-o", "test_c"
    system ENV.cxx, "-std=c++17", "test.cpp", *flags, "-o", "test_cpp"
    system "./test_c"
    system "./test_cpp"
  end
end
