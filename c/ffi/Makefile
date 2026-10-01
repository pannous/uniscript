# C/C++ library of the Rust crate: build/libuniscript.{a,dylib|so}, header ../uniscript.h, C++ wrapper ../uniscript.hpp
CARGO_TARGET_DIR ?= /opt/cargo
export CARGO_TARGET_DIR
PROFILE := release
SHARED_EXTENSION := $(if $(filter Darwin,$(shell uname)),dylib,so)
RUST_LIBRARY := $(CARGO_TARGET_DIR)/$(PROFILE)/libuniscript_ffi
BUILD := build
STATIC := $(BUILD)/libuniscript.a
SHARED := $(BUILD)/libuniscript.$(SHARED_EXTENSION)
TESTS := ../tests
FLAGS := -I.. -Wall -Wextra -Werror -g
LINK := $(STATIC) -lm $(if $(filter Darwin,$(shell uname)),,-lpthread -ldl)

# natives: the shared library per .NET/JVM runtime identifier in build/natives/<rid>/, cross-built with cargo-zigbuild
# (macOS host; Linux and Windows by cargo install cargo-zigbuild and zig; rustup target add for each target below)
NATIVES := $(BUILD)/natives
NATIVE_TARGETS := osx-arm64:aarch64-apple-darwin:libuniscript.dylib:libuniscript_ffi.dylib \
	osx-x64:x86_64-apple-darwin:libuniscript.dylib:libuniscript_ffi.dylib \
	linux-x64:x86_64-unknown-linux-gnu.2.17:libuniscript.so:libuniscript_ffi.so \
	linux-arm64:aarch64-unknown-linux-gnu.2.17:libuniscript.so:libuniscript_ffi.so \
	win-x64:x86_64-pc-windows-gnu:uniscript.dll:uniscript_ffi.dll

.PHONY: all test clean rust natives
all: $(STATIC) $(SHARED)

rust:
	cargo build --release

$(STATIC) $(SHARED): rust | $(BUILD)
	cp $(RUST_LIBRARY).a $(STATIC)
	cp $(RUST_LIBRARY).$(SHARED_EXTENSION) $(SHARED)
	$(if $(filter Darwin,$(shell uname)),install_name_tool -id @rpath/libuniscript.dylib $(SHARED))

natives:
	@set -e; for spec in $(NATIVE_TARGETS); do \
		rid=$$(echo $$spec | cut -d: -f1); target=$$(echo $$spec | cut -d: -f2); triple=$${target%.2.17}; \
		name=$$(echo $$spec | cut -d: -f3); built=$$(echo $$spec | cut -d: -f4); \
		case $$triple in *apple*) cargo build --release --target $$triple;; *) CARGO_PROFILE_RELEASE_STRIP=symbols cargo zigbuild --release --target $$target;; esac; \
		mkdir -p $(NATIVES)/$$rid; cp $(CARGO_TARGET_DIR)/$$triple/release/$$built $(NATIVES)/$$rid/$$name; \
		case $$rid in osx-*) install_name_tool -id @rpath/libuniscript.dylib $(NATIVES)/$$rid/$$name;; esac; \
	done; ls -l $(NATIVES)/*

$(BUILD):
	mkdir -p $@

$(BUILD)/test_c: $(TESTS)/test_uniscript.c $(TESTS)/cases.h ../uniscript.h $(STATIC)
	cc -std=c11 $(FLAGS) $< $(LINK) -o $@

$(BUILD)/test_cpp: $(TESTS)/test_uniscript.cpp $(TESTS)/cases.h ../uniscript.h ../uniscript.hpp $(STATIC)
	c++ -std=c++17 $(FLAGS) $< $(LINK) -o $@

# the same C test against the shared library: dyld (or ld.so) must load it
$(BUILD)/test_c_shared: $(TESTS)/test_uniscript.c $(TESTS)/cases.h ../uniscript.h $(SHARED)
	cc -std=c11 $(FLAGS) $< -L$(BUILD) -luniscript -Wl,-rpath,$(abspath $(BUILD)) -o $@

test: $(BUILD)/test_c $(BUILD)/test_cpp $(BUILD)/test_c_shared
	$(BUILD)/test_c
	$(BUILD)/test_cpp
	$(BUILD)/test_c_shared

clean:
	rm -rf $(BUILD)
