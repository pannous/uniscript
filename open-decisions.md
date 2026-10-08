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
