// The filler-free names and name endings in the JS port (tests/filler_names_test.rs is the Rust original)
import { toUnicode, toUniscript } from "../js/src/index.ts";
console.log(toUnicode("\\:syriac-letter-taw \\:syriac-taw \\:letter-taw \\:taw \\:phaistos-bee <:SYRIAC TAW/> \\:hatran-taw"), toUniscript("ܬ𐇱"));
