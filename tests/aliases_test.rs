//! Own short names of the uniscript section for characters whose Unicode names are long

use uniscript::to_unicode;

#[test]
fn world_is_the_earth_globe() {
	assert_eq!(to_unicode("\\:world"), Ok("🌍".to_string()));
	assert_eq!(to_unicode("\\:earth-globe-europe-africa"), Ok("🌍".to_string()));
}
