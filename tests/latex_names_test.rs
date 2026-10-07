//! Where HTML and LaTeX define a name differently, the LaTeX reading wins (\circ ∘, not HTML's &circ; ˆ; asymp ≍; cdot ⋅,
//! varepsilon ε) except for letters with a diacritic, which keep the HTML one (ocirc ô): user decision P198. Also the short
//! names warp's parser used before it read this index (card uniscript-index)

use uniscript::to_unicode;

fn spelled(name: &str) -> String {
	to_unicode(&format!("\\:{name}")).unwrap()
}

#[test]
fn latex_names_are_latex_glyphs() {
	// P198 exceptions: math names whose HTML reading happens to be a letter
	for (name, glyph) in [("circ", "∘"), ("asymp", "≍"), ("star", "⋆"), ("epsilon", "ε"), ("phi", "φ"), ("perp", "⟂"), ("cdot", "⋅"), ("varepsilon", "ε"), ("varphi", "φ")] {
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

#[test]
fn letter_names_are_html_letters() {
	for (name, glyph) in [("ocirc", "ô"), ("oslash", "ø"), ("imath", "ı"), ("jmath", "ȷ")] {
		assert_eq!(spelled(name), glyph, "\\:{name}");
	}
}
