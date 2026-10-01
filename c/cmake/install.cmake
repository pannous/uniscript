# install: the library, uniscript.h and uniscript.hpp, find_package(uniscript) config files and uniscript.pc
include(CMakePackageConfigHelpers)
set(UNISCRIPT_CONFIG_DIR "${CMAKE_INSTALL_LIBDIR}/cmake/uniscript")

install(TARGETS uniscript EXPORT uniscript-targets
	ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}" LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
	RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
if(UNISCRIPT_BACKEND STREQUAL "rust")
	install(FILES "${UNISCRIPT_LIBRARY}" DESTINATION "${CMAKE_INSTALL_LIBDIR}")
endif()
install(FILES ${UNISCRIPT_HEADERS} DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}")
install(EXPORT uniscript-targets NAMESPACE uniscript:: DESTINATION "${UNISCRIPT_CONFIG_DIR}")

configure_package_config_file(cmake/uniscript-config.cmake.in uniscript-config.cmake INSTALL_DESTINATION "${UNISCRIPT_CONFIG_DIR}")
write_basic_package_version_file(uniscript-config-version.cmake COMPATIBILITY SameMajorVersion)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/uniscript-config.cmake" "${CMAKE_CURRENT_BINARY_DIR}/uniscript-config-version.cmake"
	DESTINATION "${UNISCRIPT_CONFIG_DIR}")

# relative to the .pc file, so the installed tree can move (vcpkg, Conan); Debian's libdir lib/<triplet> is one level deeper
file(RELATIVE_PATH UNISCRIPT_PC_PREFIX "${CMAKE_INSTALL_FULL_LIBDIR}/pkgconfig" "${CMAKE_INSTALL_PREFIX}")
string(REGEX REPLACE "/$" "" UNISCRIPT_PC_PREFIX "${UNISCRIPT_PC_PREFIX}")
configure_file(cmake/uniscript.pc.in uniscript.pc @ONLY)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/uniscript.pc" DESTINATION "${CMAKE_INSTALL_LIBDIR}/pkgconfig")
