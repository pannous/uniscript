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

.PHONY: all test clean rust
all: $(STATIC) $(SHARED)

rust:
	cargo build --release

$(STATIC) $(SHARED): rust | $(BUILD)
	cp $(RUST_LIBRARY).a $(STATIC)
	cp $(RUST_LIBRARY).$(SHARED_EXTENSION) $(SHARED)

$(BUILD):
	mkdir -p $@

$(BUILD)/test_c: $(TESTS)/test_uniscript.c $(TESTS)/cases.h ../uniscript.h $(STATIC)
	cc -std=c11 $(FLAGS) $< $(LINK) -o $@

$(BUILD)/test_cpp: $(TESTS)/test_uniscript.cpp $(TESTS)/cases.h ../uniscript.h ../uniscript.hpp $(STATIC)
	c++ -std=c++17 $(FLAGS) $< $(LINK) -o $@

test: $(BUILD)/test_c $(BUILD)/test_cpp
	$(BUILD)/test_c
	$(BUILD)/test_cpp

clean:
	rm -rf $(BUILD)
