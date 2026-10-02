//! The chinese block types every CJK unified ideograph with a Mandarin reading: the most frequent character of a
//! reading gets it plain (yi2 疑), the others in order of frequency numbered (yi2.2 移)

use uniscript::index::{Index, Table};
use uniscript::{to_unicode, ENTITIES_INDEX};

const READINGS: [&str; 2] = ["data/sources/chinese_readings.tsv", "data/sources/unihan_readings.tsv"];

fn converts(uniscript: &str, unicode: &str) {
	assert_eq!(to_unicode(uniscript), Ok(unicode.to_string()), "{uniscript}");
}

#[test]
fn the_most_frequent_character_keeps_the_plain_reading() {
	converts("<:chinese de>", "的");
	converts("<:chinese yi1>", "一");
	converts("<:chinese di>", "第");
	converts("<:cn yi2>", "疑");
	converts("<:cn yi2.2>", "移");
	converts("<:cn yi2.3>", "遗");
	converts("<:cn shi4.2>", "事");
	converts("<:cn kou4.2>", "寇");
	converts("<:cn lve4>", "略");
	converts("<:cn lue4>", "略");
	converts("<:cn leng3>", "冷");
}

#[test]
fn rare_characters_beyond_the_frequency_list_have_their_unihan_readings() {
	converts("<:cn biang2>", "𰻝");
	converts("<:cn biang2.2>", "𰻞");
	converts("<:cn> ni3 hao3 <:/cn>", "你 好");
}

#[test]
fn every_character_and_reading_of_the_sources_can_be_typed() {
	let index = Index::new(ENTITIES_INDEX).unwrap();
	let mut pairs = 0;
	for source in READINGS {
		let text = std::fs::read_to_string(source).unwrap();
		for line in text.lines().filter(|line| !line.starts_with('#')) {
			let (character, readings) = line.split_once('\t').unwrap();
			for reading in readings.split('/') {
				let keys = (1..).map(|count| if count == 1 { format!("chinese {reading}") } else { format!("chinese {reading}.{count}") });
				let found = keys.map(|key| index.get(Table::Names, &key)).take_while(Option::is_some).any(|value| value == Some(character));
				assert!(found, "{character} {reading} in {source}");
				pairs += 1;
			}
		}
	}
	assert!(pairs > 50_000, "{pairs} readings");
}
