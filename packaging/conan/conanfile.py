# Conan 2 recipe of the native C library (c/native) from the release tarball `make -C c/native dist`.
# At a release: url and sha256 in conandata.yml, see notes/c-packaging.md. MSVC is not supported (.incbin).
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, rm


class UniscriptConan(ConanFile):
    name = "uniscript"
    version = "1.0.0"
    description = "ASCII names for Unicode text (<:alpha> -> alpha) and back: C11 library, header-only C++17 wrapper"
    license = "MIT"
    url = "https://github.com/pannous/uniscript"
    homepage = "https://pannous.com/uniscript/"
    topics = ("unicode", "entities", "text", "encoding")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def configure(self):
        # a C library: uniscript.hpp is header-only and compiled by the consumer
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("uniscript embeds its index with the assembler's .incbin: no MSVC")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        self.run("make -C c/native all")

    def package(self):
        copy(self, "LICENSE", self.build_folder, f"{self.package_folder}/licenses")
        self.run(f"make -C c/native install-lib PREFIX={self.package_folder}")
        for unwanted in ("*.a",) if self.options.shared else ("*.dylib", "*.so"):
            rm(self, unwanted, f"{self.package_folder}/lib")

    def package_info(self):
        self.cpp_info.libs = ["uniscript"]
        self.cpp_info.set_property("pkg_config_name", "uniscript")
