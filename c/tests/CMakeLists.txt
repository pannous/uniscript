# ctest: the shared reference cases (cases.h) through the C API and the C++17 wrapper, plus the native index checks
foreach(language c cpp)
	add_executable(test_uniscript_${language} test_uniscript.${language})
	target_link_libraries(test_uniscript_${language} PRIVATE uniscript::uniscript)
	add_test(NAME shared_cases_${language} COMMAND test_uniscript_${language})
endforeach()
target_compile_features(test_uniscript_cpp PRIVATE cxx_std_17)

if(UNISCRIPT_BACKEND STREQUAL "native")
	add_executable(test_native ../native/tests/test_native.c)
	target_include_directories(test_native PRIVATE ../native/src)
	target_link_libraries(test_native PRIVATE uniscript::uniscript)
	add_test(NAME native_index COMMAND test_native)
endif()
