# A project using an installed uniscript through find_package (scripts/publish.sh: CMake install, Conan, vcpkg):
#   cmake -S c/tests/consumer -B build -DCMAKE_PREFIX_PATH=<prefix> && cmake --build build && ctest --test-dir build
cmake_minimum_required(VERSION 3.16)
project(uniscript_consumer LANGUAGES C CXX)

find_package(uniscript CONFIG REQUIRED)
enable_testing()
foreach(language c cpp)
	add_executable(consumer_${language} ../../native/tests/consumer.${language})
	target_link_libraries(consumer_${language} PRIVATE uniscript::uniscript)
	add_test(NAME consumer_${language} COMMAND consumer_${language})
endforeach()
add_executable(smoke smoke.cpp)
target_link_libraries(smoke PRIVATE uniscript::uniscript)
foreach(program consumer_cpp smoke)
	target_compile_features(${program} PRIVATE cxx_std_17)
endforeach()
