# Uniscript for .NET

ASCII names for Unicode text and back: `<:alpha>` → α, `<:fracture A>` → 𝔄, `<:egyptian A1>` → 𓀀.
The NuGet package wraps the Rust reference implementation ([github.com/pannous/uniscript](https://github.com/pannous/uniscript))
through its C ABI, with the native library for osx-arm64, osx-x64, linux-x64, linux-arm64 and win-x64. .NET 8 or later.

```sh
dotnet add package Uniscript
```

```csharp
using Pannous;

Uniscript.ToUnicode("\\:alpha \\:fracture-A");             // "α 𝔄", warnings to stderr, throws UniscriptException
Uniscript.ToUniscript("α 𝔄");                             // "\\:alpha \\:fracture-A"
Uniscript.Explicit("<:alpha> <:color red A>");            // "\\:alpha <:color red A/>": inline tags in explicit form
Uniscript.Convert("<:greek q>");                          // Conversion { Text = "q", Warnings = [("no greek form of q", 0)] }
Uniscript.Convert("<:greek q>", UniscriptMode.Error);     // throws UniscriptException, Kind Unsupported
Uniscript.Convert("<:nosuch> x", UniscriptMode.Lenient);  // never throws: "<:nosuch> x" with a warning
Uniscript.Html(tagged);                                    // meta information (fonts, colors) as <span>s with CSS
Uniscript.MetaRuns(tagged);                                // plain text and its meta runs
Uniscript.Font("cuneiform-hittite");                       // lang hit-Xsux, font families, OpenType features
```

Offsets (`At`, `Start`, `End`, `Length`) are UTF-8 byte offsets, as in every uniscript library.
