# Native C uniscript: C11, no dependencies; data/entities.idx is compiled in with .incbin
#   make          build/libuniscript.a, build/libuniscript.dylib (.so elsewhere) and the command line build/uniscript
#   make test     shared reference cases (c/tests) and native tests, plain and under address+undefined sanitizers
#   make differential   the command line against the Rust reference (tests/differential.sh)
#   make install PREFIX=/usr/local [DESTDIR=]   the libraries, uniscript.h, uniscript.hpp, uniscript.pc and the command line
#   make install-lib    the same without the command line (it would clash with the Rust crate's `uniscript`)
#   make dist           build/uniscript-c-$(VERSION).tar.gz, the committed sources (git archive HEAD) with the index
#   make consumer-test  installs into CONSUMER_PREFIX and builds a C and a C++ program against it with pkg-config
#   make dist-test      unpacks the tarball into DIST_TEST, runs its tests and its consumer-test
#   make clean

ROOT := $(abspath ../..)
# the crate's version; a release tarball has no Cargo.toml and carries it in c/native/VERSION
VERSION := $(or $(shell cat VERSION 2>/dev/null),$(shell sed -n 's/^version = "\(.*\)"/\1/p' $(ROOT)/Cargo.toml | head -1))
PREFIX ?= /usr/local
LIBDIR := $(PREFIX)/lib
INCLUDEDIR := $(PREFIX)/include
BINDIR := $(PREFIX)/bin
MAN1DIR := $(PREFIX)/share/man/man1
MAN_PAGE := $(ROOT)/packaging/debian/uniscript.1
PKGCONFIGDIR := $(LIBDIR)/pkgconfig
DIST_NAME := uniscript-c-$(VERSION)
DIST_FILES := LICENSE c/uniscript.h c/uniscript.hpp c/CMakeLists.txt c/cmake c/tests c/native data/entities.idx packaging/debian/uniscript.1
CONSUMER_PREFIX ?= $(ROOT)/probes/publish/site/c
DIST_TEST := $(ROOT)/probes/publish/dist
INDEX := $(ROOT)/data/entities.idx
BUILD := build
CC ?= cc
CFLAGS ?= -O2
# -Werror only in `make test`: a downstream compiler with new warnings must not break release builds (Homebrew, Conan)
WERROR :=
WARNINGS = -std=c11 -Wall -Wextra -Wpedantic -Wno-overlength-strings $(WERROR)
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

.PHONY: all test clean differential install install-lib install-cli dist consumer-test dist-test
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

# room in the header, so install (and Homebrew) can set the absolute install name
$(BUILD)/libuniscript.$(SHARED_EXTENSION): $(OBJECTS)
	$(CC) -shared $(if $(DARWIN),-install_name @rpath/libuniscript.dylib -headerpad_max_install_names) $^ -o $@

$(BUILD)/test_%: tests/test_%.c $(OBJECTS) $(HEADERS)
	$(CC) $(WARNINGS) $(INCLUDES) $< $(OBJECTS) -o $@
$(BUILD)/test_%: ../tests/test_%.c ../tests/cases.h $(OBJECTS) $(HEADERS)
	$(CC) $(WARNINGS) $(INCLUDES) $< $(OBJECTS) -o $@
$(BUILD)/test_%_cpp: ../tests/test_%.cpp ../tests/cases.h ../uniscript.hpp $(OBJECTS) $(HEADERS)
	$(CXX) -std=c++17 -Wall -Wextra -Werror -I.. $< $(OBJECTS) -o $@
$(BUILD)/sanitized/test_%_cpp: ../tests/test_%.cpp ../tests/cases.h ../uniscript.hpp $(SANITIZED_OBJECTS) $(HEADERS)
	$(CXX) -std=c++17 -Wall -Wextra -Werror $(SANITIZE) -I.. $< $(SANITIZED_OBJECTS) -o $@
$(BUILD)/sanitized/test_%: tests/test_%.c $(SANITIZED_OBJECTS) $(HEADERS)
	$(CC) $(WARNINGS) $(SANITIZE) $(INCLUDES) $< $(SANITIZED_OBJECTS) -o $@
$(BUILD)/sanitized/test_%: ../tests/test_%.c ../tests/cases.h $(SANITIZED_OBJECTS) $(HEADERS)
	$(CC) $(WARNINGS) $(SANITIZE) $(INCLUDES) $< $(SANITIZED_OBJECTS) -o $@

TEST_NAMES := $(notdir $(subst .cpp,_cpp,$(TESTS:.c=)))
TEST_BINARIES := $(foreach test,$(TEST_NAMES),$(BUILD)/$(test) $(BUILD)/sanitized/$(test))
test: WERROR := -Werror
test: $(TEST_BINARIES)
	@for binary in $^; do echo "== $$binary"; ASAN_OPTIONS=detect_leaks=$(if $(DARWIN),0,1) $$binary || exit 1; done
	@$(if $(DARWIN),for binary in $(TEST_NAMES); do leaks --quiet --atExit -- $(BUILD)/$$binary >/dev/null 2>&1 || { echo "leaks in $$binary"; exit 1; }; done; echo "== no leaks (macOS leaks)")

$(BUILD):
	mkdir -p $@

clean:
	rm -rf $(BUILD)

install: install-lib install-cli

install-cli: $(BUILD)/uniscript
	install -d $(DESTDIR)$(BINDIR) $(DESTDIR)$(MAN1DIR)
	install -m 755 $< $(DESTDIR)$(BINDIR)
	install -m 644 $(MAN_PAGE) $(DESTDIR)$(MAN1DIR)

install-lib: $(BUILD)/libuniscript.a $(BUILD)/libuniscript.$(SHARED_EXTENSION) $(BUILD)/uniscript.pc
	install -d $(DESTDIR)$(LIBDIR) $(DESTDIR)$(INCLUDEDIR) $(DESTDIR)$(PKGCONFIGDIR)
	install -m 644 $(BUILD)/libuniscript.a $(DESTDIR)$(LIBDIR)
	install -m 755 $(BUILD)/libuniscript.$(SHARED_EXTENSION) $(DESTDIR)$(LIBDIR)
	$(if $(DARWIN),install_name_tool -id $(LIBDIR)/libuniscript.dylib $(DESTDIR)$(LIBDIR)/libuniscript.dylib)
	install -m 644 ../uniscript.h ../uniscript.hpp $(DESTDIR)$(INCLUDEDIR)
	install -m 644 $(BUILD)/uniscript.pc $(DESTDIR)$(PKGCONFIGDIR)

# rebuilt on every install: it holds PREFIX
$(BUILD)/uniscript.pc: FORCE | $(BUILD)
	printf '%s\n' 'prefix=$(PREFIX)' 'libdir=$(LIBDIR)' 'includedir=$(INCLUDEDIR)' '' 'Name: uniscript' \
		'Description: ASCII names for Unicode text and back (C11, C++17 wrapper uniscript.hpp)' \
		'Version: $(VERSION)' 'URL: https://github.com/pannous/uniscript' \
		'Libs: -L$${libdir} -luniscript' 'Cflags: -I$${includedir}' > $@

dist: | $(BUILD)
	git -C $(ROOT) archive --format=tar.gz --prefix=$(DIST_NAME)/ --add-virtual-file=$(DIST_NAME)/c/native/VERSION:$(VERSION) \
		-o $(abspath $(BUILD))/$(DIST_NAME).tar.gz HEAD $(DIST_FILES)
	@echo "$(BUILD)/$(DIST_NAME).tar.gz sha256 $$(shasum -a 256 $(BUILD)/$(DIST_NAME).tar.gz | cut -d' ' -f1)"

# a fresh CONSUMER_PREFIX each time, so the programs cannot pick up an older install
consumer-test:
	rm -rf $(CONSUMER_PREFIX)
	$(MAKE) install PREFIX=$(CONSUMER_PREFIX)
	$(CONSUMER_PREFIX)/bin/uniscript '<:alpha> <:fracture A>'
	export PKG_CONFIG_PATH=$(CONSUMER_PREFIX)/lib/pkgconfig; RPATH=-Wl,-rpath,$(CONSUMER_PREFIX)/lib; \
	$(CC) $(WARNINGS) tests/consumer.c $$(pkg-config --cflags --libs uniscript) $$RPATH -o $(BUILD)/consumer_c && \
	$(CXX) -std=c++17 -Wall -Wextra -Werror tests/consumer.cpp $$(pkg-config --cflags --libs uniscript) $$RPATH -o $(BUILD)/consumer_cpp
	$(BUILD)/consumer_c
	$(BUILD)/consumer_cpp

dist-test: dist
	mkdir -p $(DIST_TEST) && rm -rf $(DIST_TEST)/$(DIST_NAME) && tar xzf $(BUILD)/$(DIST_NAME).tar.gz -C $(DIST_TEST)
	$(MAKE) -C $(DIST_TEST)/$(DIST_NAME)/c/native all test consumer-test CONSUMER_PREFIX=$(CONSUMER_PREFIX)

FORCE:

# the native command line against the Rust reference on the repo's markdown and a random corpus (needs cargo)
differential: $(BUILD)/uniscript
	tests/differential.sh
