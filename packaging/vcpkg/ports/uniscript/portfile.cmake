# the release tarball of `make -C c/native dist`: c/native (plain C) built with c/CMakeLists.txt; MSVC lacks .incbin
vcpkg_download_distfile(ARCHIVE
    URLS "https://github.com/pannous/uniscript/releases/download/v${VERSION}/uniscript-c-${VERSION}.tar.gz"
    FILENAME "uniscript-c-${VERSION}.tar.gz"
    SHA512 e84868658976147f6e1b228f756e25c1ec50e8ca9ac1f22823e0d22f8a5c6a80d378e7bffb62286c8f80f451fdcd2ec6362e742e123c3ed1ad0c167e38233edc
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
