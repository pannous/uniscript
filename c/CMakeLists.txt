# uniscript for C11 and C++17 (uniscript.h, header-only uniscript.hpp): the library uniscript::uniscript
#   cmake -S c -B build && cmake --build build && ctest --test-dir build   shared reference cases through C and C++
#   cmake --install build --prefix …   then find_package(uniscript CONFIG REQUIRED), target_link_libraries(app uniscript::uniscript)
# UNISCRIPT_BACKEND: native (c/native, plain C, needs only a C compiler; the packages build this one) or rust (c/ffi,
# the Rust crate behind the same C ABI, needs cargo and the whole repository). BUILD_SHARED_LIBS: shared or static.
cmake_minimum_required(VERSION 3.16)

set(UNISCRIPT_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
# the crate's version; a release tarball has no Cargo.toml and carries it in c/native/VERSION
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/native/VERSION")
	file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/native/VERSION" UNISCRIPT_VERSION LIMIT_COUNT 1)
else()
	file(STRINGS "${UNISCRIPT_ROOT}/Cargo.toml" UNISCRIPT_VERSION REGEX "^version = " LIMIT_COUNT 1)
	string(REGEX REPLACE "^version = \"(.*)\"" "\\1" UNISCRIPT_VERSION "${UNISCRIPT_VERSION}")
endif()

project(uniscript VERSION ${UNISCRIPT_VERSION} DESCRIPTION "ASCII names for Unicode text and back" LANGUAGES C)

string(COMPARE EQUAL "${CMAKE_SOURCE_DIR}" "${CMAKE_CURRENT_SOURCE_DIR}" UNISCRIPT_TOP_LEVEL)
set(UNISCRIPT_BACKEND native CACHE STRING "native (c/native) or rust (c/ffi)")
set_property(CACHE UNISCRIPT_BACKEND PROPERTY STRINGS native rust)
option(UNISCRIPT_TESTS "build the tests (ctest)" ${UNISCRIPT_TOP_LEVEL})
option(UNISCRIPT_INSTALL "install the library, headers, CMake config and pkg-config file" ${UNISCRIPT_TOP_LEVEL})
set(UNISCRIPT_INDEX "${UNISCRIPT_ROOT}/data/entities.idx")
set(UNISCRIPT_HEADERS "${CMAKE_CURRENT_SOURCE_DIR}/uniscript.h" "${CMAKE_CURRENT_SOURCE_DIR}/uniscript.hpp")

include(GNUInstallDirs)

if(UNISCRIPT_BACKEND STREQUAL "native")
	if(MSVC)
		message(FATAL_ERROR "uniscript embeds its index with the assembler's .incbin: no MSVC (clang or gcc, also MinGW)")
	endif()
	if(APPLE)
		# Apple's ar leaves members after the odd-sized index object unaligned; libtool aligns them
		set(CMAKE_C_CREATE_STATIC_LIBRARY "libtool -static -o <TARGET> <OBJECTS>")
	endif()
	file(GLOB UNISCRIPT_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/native/src/*.c")
	add_library(uniscript ${UNISCRIPT_SOURCES})
	target_compile_features(uniscript PRIVATE c_std_11)
	target_compile_definitions(uniscript PRIVATE "UNISCRIPT_INDEX_PATH=\"${UNISCRIPT_INDEX}\"")
	target_include_directories(uniscript PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/native/src")
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/native/src/index.c" PROPERTIES OBJECT_DEPENDS "${UNISCRIPT_INDEX}")
	set_target_properties(uniscript PROPERTIES VERSION ${PROJECT_VERSION} SOVERSION ${PROJECT_VERSION_MAJOR})
	if(APPLE)
		target_link_options(uniscript PRIVATE -Wl,-headerpad_max_install_names)
	endif()
elseif(UNISCRIPT_BACKEND STREQUAL "rust")
	include(cmake/rust_backend.cmake)
else()
	message(FATAL_ERROR "UNISCRIPT_BACKEND is native or rust, not ${UNISCRIPT_BACKEND}")
endif()

# the rust backend is an INTERFACE library, which takes no PUBLIC usage requirements
get_target_property(UNISCRIPT_TYPE uniscript TYPE)
if(UNISCRIPT_TYPE STREQUAL "INTERFACE_LIBRARY")
	set(UNISCRIPT_SCOPE INTERFACE)
else()
	set(UNISCRIPT_SCOPE PUBLIC)
endif()
target_include_directories(uniscript ${UNISCRIPT_SCOPE}
	"$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>" "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>")
add_library(uniscript::uniscript ALIAS uniscript)

if(UNISCRIPT_TESTS)
	enable_language(CXX)
	enable_testing()
	add_subdirectory(tests)
endif()

if(UNISCRIPT_INSTALL)
	include(cmake/install.cmake)
endif()
