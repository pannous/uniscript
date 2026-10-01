# Homebrew formula for the tap pannous/homebrew-tap (brew install pannous/tap/uniscript; the alias libuniscript names it
# too): the Rust command line `uniscript` from the crates.io crate, plus the native C11 library (c/native) with
# uniscript.h, the C++17 wrapper uniscript.hpp, the CMake package uniscript::uniscript and uniscript.pc, from the C tarball
# `make -C c/native dist` attached to the GitHub release. One formula, because Homebrew 7 refuses dependencies from
# untrusted taps. At a release: both sha256, see notes/packaging-homebrew.md
class Uniscript < Formula
  desc "ASCII names for Unicode text (<:alpha> → α, <:fracture A> → 𝔄) and back"
  homepage "https://pannous.com/uniscript/"
  license "MIT"
  revision 1
  head "https://github.com/pannous/uniscript.git", branch: "main"

  stable do
    url "https://static.crates.io/crates/uniscript/uniscript-1.0.0.crate"
    sha256 "eccef344fd6ef4e31488e9c303631380b76312317204357926332ac875c85793"

    resource "libuniscript" do
      url "https://github.com/pannous/uniscript/releases/download/v1.0.0/uniscript-c-1.0.0.tar.gz"
      sha256 "516c9da07911ac5866cd7ccf37e8efc667d15e1d4450ffa3a4566e84f89f8ccf"
    end
  end

  depends_on "cmake" => [:build, :test]
  depends_on "rust" => :build
  depends_on "pkgconf" => :test

  def install
    system "cargo", "install", *std_cargo_args
    if build.head?
      install_library
    else
      resource("libuniscript").stage { install_library }
    end
  end

  # the C library from the c/ folder of the current directory: shared with the CMake package, then the static archive
  def install_library
    args = %w[-DUNISCRIPT_TESTS=OFF -DUNISCRIPT_INSTALL=ON]
    system "cmake", "-S", "c", "-B", "build", "-DBUILD_SHARED_LIBS=ON", *args, *std_cmake_args
    system "cmake", "--build", "build"
    system "cmake", "--install", "build"
    system "cmake", "-S", "c", "-B", "build-static", "-DBUILD_SHARED_LIBS=OFF", *args, *std_cmake_args
    system "cmake", "--build", "build-static"
    lib.install "build-static/libuniscript.a"
  end

  test do
    assert_equal "α 𝔄", shell_output("#{bin}/uniscript '<:alpha> <:fracture A>'").strip
    assert_equal "<:alpha> <:fracture A>", shell_output("#{bin}/uniscript -r 'α 𝔄'").strip

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

    (testpath/"CMakeLists.txt").write <<~CMAKE
      cmake_minimum_required(VERSION 3.16)
      project(consumer LANGUAGES CXX)
      find_package(uniscript CONFIG REQUIRED)
      add_executable(consumer test.cpp)
      target_compile_features(consumer PRIVATE cxx_std_17)
      target_link_libraries(consumer PRIVATE uniscript::uniscript)
    CMAKE
    system "cmake", "-S", ".", "-B", "build", "-DCMAKE_PREFIX_PATH=#{opt_prefix}"
    system "cmake", "--build", "build"
    system "./build/consumer"
  end
end
