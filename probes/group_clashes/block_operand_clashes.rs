// Operands of the egyptian block (and every block) that are themselves block names: inline tags read them as stacked
// blocks/effects, e.g. <:egyptian red A1> is meant as an effect but <:egyptian X …> with X a block is not an operand
use uniscript::index::{Index, Table};
use std::collections::BTreeSet;
fn main() {
	let index = Index::new(uniscript::ENTITIES_INDEX).unwrap();
	let names: Vec<(&str, &str)> = index.entries(Table::Names).collect();
	let blocks: BTreeSet<&str> = names.iter().filter_map(|(key, _)| key.strip_suffix(' ')).filter(|b| !b.contains(' ')).collect();
	println!("{} blocks", blocks.len());
	let mut per_block: std::collections::BTreeMap<&str, Vec<&str>> = Default::default();
	for (key, _) in &names {
		if let Some((block, operand)) = key.split_once(' ') {
			if blocks.contains(block) && blocks.contains(operand) { per_block.entry(block).or_default().push(operand); }
		}
	}
	for (block, operands) in &per_block { println!("{block}: {}", operands.join(" ")); }
	let egyptian: Vec<&str> = names.iter().filter_map(|(key, _)| key.strip_prefix("egyptian ")).filter(|o| !o.starts_with('*')).collect();
	let first_words: BTreeSet<&str> = egyptian.iter().map(|o| o.split('-').next().unwrap()).filter(|w| blocks.contains(w)).collect();
	println!("egyptian operands {}; first words of multi-word descriptions that are blocks: {first_words:?}", egyptian.len());
	let plain_names: Vec<&&str> = egyptian.iter().filter(|o| !o.contains('-') && index.get(Table::Names, o).is_some()).take(40).collect();
	println!("egyptian operands that are also global names (sample): {plain_names:?}");
}
