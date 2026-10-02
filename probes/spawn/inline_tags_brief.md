# Port brief: inline tags warn, <:…/> self-closes, explicit()

Reference: Rust core, commits 8ed80c0 (src/lib.rs, src/main.rs, tests/inline_tags_test.rs) and 748be1f (shared cases
js/test/cases.json: new `explicit` section, new `warns` and `quiet` cases, rewritten `roundTrips`/`toUniscript`/`quiet`/
`lenient`). Read `git show 8ed80c0 -- src/lib.rs` first: port exactly that behaviour.

1. Inline tags warn: a `<:content>` that converts without any other warning and reads as an opener warns
   `<:content> looks like an opening tag: write FORMS` at the tag's byte offset. "Reads as an opener": content longer
   than 1 byte, not closing (`<:>`, `<:/x>`), not ending in `/`, not a block word (`<:greek>`), not a meta span opener
   (meta keys with values only: `<:font han-japanese>`). One warning per tag: no opener warning if the tag already warned.
2. FORMS, in this order, joined "a, b or c" (two: "a or b", one: "a"):
   - `\:` + content with spaces as hyphens, only if content is name characters [A-Za-z0-9_-] and spaces, does not mix
     hyphens with spaces, does not start with a meta key (`<:color red A>`), and the next character after `>` is no name
     character;
   - `<:block> operand <:/block>` if content is exactly two words, the first a block, the second no block;
   - `<:content/>` always.
3. `<:content/>` (content without the slash non-empty) converts like the inline tag, without the opener warning.
4. `explicit(source)`: the source with each opener-like inline tag replaced by its `\:` form if offered, else `<:…/>`;
   the header (`<:uniscript …>` at the very start) and everything else stay. Expose it in the port's public API.
5. `toUniscript(text)` returns `explicit(…)` of what it produced before, so reverse output is explicit.
6. Tests: the shared cases (js/test/cases.json) must pass, including the new `explicit` section (add a runner for it).
   Port-specific tests that asserted the old reverse spelling or no warnings for bare inline tags: update them to the
   explicit spelling, as the Rust tests were updated in 8ed80c0 (the user decided this language-wide change).
