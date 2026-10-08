# Open decisions

- **Greek final sigma** (TODO.md lines on αθοσ / κοσμοσ): `<:greek> kosmos <:/greek>` → κοσμος? Needs ~15 existing
  shared cases (js/test/cases.json, c/tests/cases.h, tests/*.rs) and the spec examples in docs/uniscript.md to change,
  which only you can approve. Recommendation: yes, as a data-driven block control (`"*final σ": "ς"`: σ after a letter
  and before a non-letter takes ς), so other scripts with final forms (Hebrew ך ם ן ף ץ) can reuse it.
- **Short names for scripts other than Latin** (2026-10-08): `\:cyrillic-zhe`, `\:greek-Omega`-style names keep the
  script word; only Latin, the default, drops it. Alternative: drop the script when the rest is unique across scripts too.
- **`data/uniscript_index.py seed`**: it would overwrite all hand edits made since the split (latex extras, P198, own
  names, descriptions, hair styles). Recommendation: retire `seed` (the wasp files are the ground truth; git keeps the
  seeder), or turn it into a merge that only adds new Unicode names.
- **Egyptian Extended-A over the private use signs**: 2837 Extended-A signs carry a JSesh number that the extended sign
  list (gardiner.full.csv, Aegyptus private use) also has, for the same sign (`<:gardiner Q4A>`: U+F446E there, 𔂦
  U+140A6 in Unicode 16). Tests in tests/uniscript_test.rs pin the private use sign. Recommendation: let Unicode win
  (standard characters, readable without Aegyptus) and change those three assertions; 110 of Unikemet's own numbers
  differ from JSesh's and stay behind the JSesh meaning either way.
- **Chinese neutral tone**: neutral-tone readings are stored without tone and numbered (`shi.2` 匙 of 钥匙), so the
  toneless `shi` list mixes them in (是 twice). Recommendation: neutral tone as tone 5 (`shi5` 匙); changes the Sublime
  test that pins `shi.2` → 匙.
