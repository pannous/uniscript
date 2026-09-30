# conan create packaging/conan: builds the C and C++ consumers of c/native/tests against the package with pkg-config
import os

from conan import ConanFile

CONSUMERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../c/native/tests")


class UniscriptTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"

    def layout(self):
        self.folders.build = self.folders.generators = "build"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        flags = f"$(PKG_CONFIG_PATH={self.generators_folder} pkg-config --cflags --libs uniscript)"
        self.run(f"cc -std=c11 {CONSUMERS}/consumer.c {flags} -o consumer_c")
        self.run(f"c++ -std=c++17 {CONSUMERS}/consumer.cpp {flags} -o consumer_cpp")

    def test(self):
        self.run("./consumer_c", env="conanrun")
        self.run("./consumer_cpp", env="conanrun")
