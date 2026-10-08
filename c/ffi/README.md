# uniscript C/C++ (Rust-backed)

The Rust crate behind the C ABI of `../uniscript.h`, with the header-only C++17 wrapper `../uniscript.hpp`.

```sh
make          # build/libuniscript.a and build/libuniscript.dylib (.so on Linux)
make test     # the reference cases in ../tests through C and C++
```

```c
#include "uniscript.h"   // cc -I c app.c c/ffi/build/libuniscript.a -lm
uniscript_result result = uniscript_convert("<:alpha> <:fracture 7>", UNISCRIPT_WARN);
// result.text "α 7", result.warnings[0].message "no fracture form of 7"
uniscript_result_free(&result);
char *spelled = uniscript_to_uniscript("α 𝔄");   // "<:alpha> <:fracture A>"
uniscript_free(spelled);
```

```cpp
#include "uniscript.hpp"   // c++ -std=c++17 -I c app.cpp c/ffi/build/libuniscript.a -lm
uniscript::to_unicode("<:alpha> <:fracture A>");                // "α 𝔄", throws uniscript::Error
auto [text, warnings] = uniscript::convert("<:greek q>");       // "q", {{"no greek form of q", 0}}
uniscript::convert("<:nosuch>", uniscript::Mode::Lenient).text;  // "<:nosuch>", with a warning
uniscript::to_uniscript("α 𝔄");                                // "<:alpha> <:fracture A>"
uniscript::html(tagged).text;                                   // meta information as <span>s with CSS
```
