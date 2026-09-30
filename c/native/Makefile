# Native C uniscript: C11, no dependencies; data/entities.idx is compiled in with .incbin
#   make          build/libuniscript.a, build/libuniscript.dylib (.so elsewhere) and the command line build/uniscript
#   make test     shared reference cases (c/tests) and native tests, plain and under address+undefined sanitizers
#   make differential   the command line against the Rust reference (tests/differential.sh)
#   make clean

ROOT := $(abspath ../..)
INDEX := $(ROOT)/data/entities.idx
BUILD := build
CC ?= cc
CFLAGS ?= -O2
WARNINGS := -std=c11 -Wall -Wextra -Wpedantic -Wno-overlength-strings -Wno-missing-field-initializers -Werror
INCLUDES := -I.. -Isrc
DEFINES := -DUNISCRIPT_INDEX_PATH='"$(INDEX)"'
SANITIZE := -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all -g -O1
DARWIN := $(filter Darwin,$(shell uname -s))
SHARED_EXTENSION := $(if $(DARWIN),dylib,so)
# Apple's ar leaves members after the odd-sized index object unaligned; libtool aligns them
ARCHIVE := $(if $(DARWIN),libtool -static -o,$(AR) rcs)

SOURCES := $(wildcard src/*.c)
HEADERS := ../uniscript.h src/internal.h
OBJECTS := $(SOURCES:src/%.c=$(BUILD)/%.o)
SANITIZED_OBJECTS := $(SOURCES:src/%.c=$(BUILD)/sanitized/%.o)
TESTS := ../tests/test_uniscript.c ../tests/test_uniscript.cpp tests/test_native.c
CXX ?= c++

.PHONY: all test clean differential
.SECONDARY:
all: $(BUILD)/libuniscript.a $(BUILD)/libuniscript.$(SHARED_EXTENSION) $(BUILD)/uniscript

$(BUILD)/%.o: src/%.c $(HEADERS) $(INDEX) | $(BUILD)
	$(CC) $(WARNINGS) $(CFLAGS) -fPIC $(INCLUDES) $(DEFINES) -c $< -o $@

$(BUILD)/sanitized/%.o: src/%.c $(HEADERS) $(INDEX) | $(BUILD)
	@mkdir -p $(BUILD)/sanitized
	$(CC) $(WARNINGS) $(SANITIZE) $(INCLUDES) $(DEFINES) -c $< -o $@

$(BUILD)/libuniscript.a: $(OBJECTS)
	$(ARCHIVE) $@ $^

$(BUILD)/uniscript: cli.c $(BUILD)/libuniscript.a ../uniscript.h
	$(CC) $(WARNINGS) $(CFLAGS) $(INCLUDES) $< $(BUILD)/libuniscript.a -o $@

$(BUILD)/libuniscript.$(SHARED_EXTENSION): $(OBJECTS)
	$(CC) -shared $^ -o $@

$(BUILD)/test_%: tests/test_%.c $(OBJECTS) $(HEADERS)
	$(CC) $(WARNINGS) $(INCLUDES) $< $(OBJECTS) -o $@
$(BUILD)/test_%: ../tests/test_%.c ../tests/cases.h $(OBJECTS) $(HEADERS)
	$(CC) $(WARNINGS) $(INCLUDES) $< $(OBJECTS) -o $@
$(BUILD)/test_%_cpp: ../tests/test_%.cpp ../tests/cases.h ../uniscript.hpp $(OBJECTS) $(HEADERS)
	$(CXX) -std=c++17 -Wall -Wextra -Wno-missing-field-initializers -Werror -I.. $< $(OBJECTS) -o $@
$(BUILD)/sanitized/test_%_cpp: ../tests/test_%.cpp ../tests/cases.h ../uniscript.hpp $(SANITIZED_OBJECTS) $(HEADERS)
	$(CXX) -std=c++17 -Wall -Wextra -Wno-missing-field-initializers -Werror $(SANITIZE) -I.. $< $(SANITIZED_OBJECTS) -o $@
$(BUILD)/sanitized/test_%: tests/test_%.c $(SANITIZED_OBJECTS) $(HEADERS)
	$(CC) $(WARNINGS) $(SANITIZE) $(INCLUDES) $< $(SANITIZED_OBJECTS) -o $@
$(BUILD)/sanitized/test_%: ../tests/test_%.c ../tests/cases.h $(SANITIZED_OBJECTS) $(HEADERS)
	$(CC) $(WARNINGS) $(SANITIZE) $(INCLUDES) $< $(SANITIZED_OBJECTS) -o $@

TEST_NAMES := $(notdir $(subst .cpp,_cpp,$(TESTS:.c=)))
TEST_BINARIES := $(foreach test,$(TEST_NAMES),$(BUILD)/$(test) $(BUILD)/sanitized/$(test))
test: $(TEST_BINARIES)
	@for binary in $^; do echo "== $$binary"; ASAN_OPTIONS=detect_leaks=$(if $(DARWIN),0,1) $$binary || exit 1; done
	@$(if $(DARWIN),for binary in $(TEST_NAMES); do leaks --quiet --atExit -- $(BUILD)/$$binary >/dev/null 2>&1 || { echo "leaks in $$binary"; exit 1; }; done; echo "== no leaks (macOS leaks)")

$(BUILD):
	mkdir -p $@

clean:
	rm -rf $(BUILD)

# the native command line against the Rust reference on the repo's markdown and a random corpus (needs cargo)
differential: $(BUILD)/uniscript
	tests/differential.sh
