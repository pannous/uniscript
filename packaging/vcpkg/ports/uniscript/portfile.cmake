# the release tarball of `make -C c/native dist`: c/native (plain C) built with c/CMakeLists.txt; MSVC lacks .incbin
vcpkg_download_distfile(ARCHIVE
    URLS "https://github.com/pannous/uniscript/releases/download/v${VERSION}/uniscript-c-${VERSION}.tar.gz"
    FILENAME "uniscript-c-${VERSION}.tar.gz"
    SHA512 85274aa850bbc196d4ce0ca82f29dfbb2aba60ee26944fc18126080923cfd11ba5bae8f4787e36aaa2fec3af8ce6239fb477b2612c2a6e4e4882363e70264693
)
vcpkg_extract_source_archive(SOURCE_PATH ARCHIVE "${ARCHIVE}")

vcpkg_cmake_configure(
    SOURCE_PATH "${SOURCE_PATH}/c"
    OPTIONS -DUNISCRIPT_TESTS=OFF -DUNISCRIPT_INSTALL=ON
)
vcpkg_cmake_install()
vcpkg_cmake_config_fixup(CONFIG_PATH lib/cmake/uniscript)
vcpkg_fixup_pkgconfig()

file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/include")
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
