# Port brief: "*readings" blocks split unknown words into whole readings

Reference: Rust core commit c9cd2a1 (src/lib.rs: READINGS_KEY, operand(), readings(); tests/block_readings_test.rs;
shared cases js/test/cases.json: new quiet cases shihan, woaini, shi han nuli, nu3li4, <:chinese shihan/>, greek metal,
and warns cases abcde / qqq). Read `git show c9cd2a1 -- src/lib.rs` first and port exactly that behaviour.

1. A block whose data has the control key "*readings" (chinese, cuneiform; in data/entities.idx, rebuilt in c9cd2a1)
   reads a word that is none of its operands as whole readings: split the word at character boundaries into operands of
   the block, the fewest pieces; of equally few, the longest first piece (dynamic programming over the word, longest
   piece tried first). Each piece converts like an own operand (effect suffixes as for an own entry). Silent: no warning.
2. If the word does not split completely, it stays as written with one warning `no <block> form of <word>` at the same
   offset the port uses for other block-text warnings (Rust: the block text start, 11 in `<:chinese> abcde <:/chinese>`).
3. Blocks without "*readings" (greek …) keep the old letter/digraph spelling unchanged.
4. Shared cases must pass; existing port tests stay untouched unless they assert the old letter splitting of a chinese
   or cuneiform word (then mirror c9cd2a1 and say so in your report).
See notes/footguns.md for why the silent split is intended.
