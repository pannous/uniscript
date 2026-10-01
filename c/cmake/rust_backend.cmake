# UNISCRIPT_BACKEND=rust: c/ffi built by cargo, wrapped as an INTERFACE library linking its static or shared library
find_program(CARGO cargo REQUIRED)
set(UNISCRIPT_CARGO_TARGET_DIR "$ENV{CARGO_TARGET_DIR}" CACHE PATH "cargo's target directory (default: in the build tree)")
if(NOT UNISCRIPT_CARGO_TARGET_DIR)
	set(UNISCRIPT_CARGO_TARGET_DIR "${CMAKE_CURRENT_BINARY_DIR}/cargo")
endif()
if(BUILD_SHARED_LIBS)
	set(UNISCRIPT_RUST_FILE "${CMAKE_SHARED_LIBRARY_PREFIX}uniscript_ffi${CMAKE_SHARED_LIBRARY_SUFFIX}")
	set(UNISCRIPT_LIBRARY_FILE "${CMAKE_SHARED_LIBRARY_PREFIX}uniscript${CMAKE_SHARED_LIBRARY_SUFFIX}")
else()
	set(UNISCRIPT_RUST_FILE "${CMAKE_STATIC_LIBRARY_PREFIX}uniscript_ffi${CMAKE_STATIC_LIBRARY_SUFFIX}")
	set(UNISCRIPT_LIBRARY_FILE "${CMAKE_STATIC_LIBRARY_PREFIX}uniscript${CMAKE_STATIC_LIBRARY_SUFFIX}")
endif()
set(UNISCRIPT_LIBRARY "${CMAKE_CURRENT_BINARY_DIR}/${UNISCRIPT_LIBRARY_FILE}")

# cargo decides what is stale, so it runs on every build; the copy carries the library's name
add_custom_target(uniscript_cargo ALL
	COMMAND "${CMAKE_COMMAND}" -E env "CARGO_TARGET_DIR=${UNISCRIPT_CARGO_TARGET_DIR}"
		"${CARGO}" build --release --manifest-path "${CMAKE_CURRENT_SOURCE_DIR}/ffi/Cargo.toml"
	COMMAND "${CMAKE_COMMAND}" -E copy_if_different "${UNISCRIPT_CARGO_TARGET_DIR}/release/${UNISCRIPT_RUST_FILE}" "${UNISCRIPT_LIBRARY}"
	COMMAND $<$<AND:$<PLATFORM_ID:Darwin>,$<BOOL:${BUILD_SHARED_LIBS}>>:install_name_tool$<SEMICOLON>-id$<SEMICOLON>@rpath/${UNISCRIPT_LIBRARY_FILE}$<SEMICOLON>${UNISCRIPT_LIBRARY}>
	BYPRODUCTS "${UNISCRIPT_LIBRARY}"
	COMMAND_EXPAND_LISTS
	COMMENT "cargo build c/ffi")

# imported, so CMake gives the build tree's programs an rpath to the shared library
if(BUILD_SHARED_LIBS)
	add_library(uniscript_rust SHARED IMPORTED)
	set_target_properties(uniscript_rust PROPERTIES IMPORTED_SONAME "@rpath/${UNISCRIPT_LIBRARY_FILE}")
else()
	add_library(uniscript_rust STATIC IMPORTED)
endif()
set_target_properties(uniscript_rust PROPERTIES IMPORTED_LOCATION "${UNISCRIPT_LIBRARY}")
add_dependencies(uniscript_rust uniscript_cargo)

find_package(Threads REQUIRED)
add_library(uniscript INTERFACE)
target_link_libraries(uniscript INTERFACE
	"$<BUILD_INTERFACE:uniscript_rust>" "$<INSTALL_INTERFACE:$<INSTALL_PREFIX>/${CMAKE_INSTALL_LIBDIR}/${UNISCRIPT_LIBRARY_FILE}>"
	Threads::Threads ${CMAKE_DL_LIBS} $<$<NOT:$<PLATFORM_ID:Darwin,Windows>>:m>)
