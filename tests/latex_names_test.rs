//! LaTeX command names win over the HTML entities of the same name (\circ is ∘, not HTML's &circ; ˆ; HTML swaps
//! varepsilon/varphi), and the short names warp's parser used before it read this index (card uniscript-index)

use uniscript::to_unicode;

fn spelled(name: &str) -> String {
	to_unicode(&format!("\\:{name}")).unwrap()
}

#[test]
fn latex_names_are_latex_glyphs() {
	for (name, glyph) in [("circ", "∘"), ("varepsilon", "ε"), ("varphi", "φ"), ("epsilon", "ε"), ("phi", "φ"), ("perp", "⟂")] {
		assert_eq!(spelled(name), glyph, "\\:{name}");
	}
}

#[test]
fn short_math_names() {
	let names = [("nat", "ℕ"), ("complex", "ℂ"), ("euler", "ℯ"), ("degree", "°"), ("cbrt", "∛"), ("to", "→"), ("neq", "≠"),
		("land", "∧"), ("lor", "∨"), ("lnot", "¬"), ("ldots", "…"), ("dots", "…")];
	for (name, glyph) in names {
		assert_eq!(spelled(name), glyph, "\\:{name}");
	}
}
