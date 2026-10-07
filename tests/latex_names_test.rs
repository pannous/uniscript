//! Where HTML and LaTeX define a name differently, a letter takes the HTML reading and anything else the LaTeX one (user
//! decision P198: ocirc ô, asymp ≍, \circ ∘ not HTML's &circ; ˆ), and the short names warp's parser used before it read
//! this index (card uniscript-index)

use uniscript::to_unicode;

fn spelled(name: &str) -> String {
	to_unicode(&format!("\\:{name}")).unwrap()
}

#[test]
fn latex_names_are_latex_glyphs() {
	for (name, glyph) in [("circ", "∘"), ("asymp", "≍"), ("star", "⋆"), ("epsilon", "ε"), ("phi", "φ"), ("perp", "⟂")] {
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
	for (name, glyph) in [("ocirc", "ô"), ("oslash", "ø"), ("cdot", "ċ"), ("imath", "ı"), ("varepsilon", "ϵ"), ("varphi", "ϕ")] {
		assert_eq!(spelled(name), glyph, "\\:{name}");
	}
}
