//! Nicknames (data/entities/nicknames.wasp): names Unicode never gave a character, read but never written back

use uniscript::{to_unicode, to_uniscript};

#[test]
fn bee_and_wasp_are_the_honeybee() {
	assert_eq!(to_unicode("\\:bee \\:wasp").as_deref(), Ok("🐝 🐝"));
	assert_eq!(to_uniscript("🐝"), "\\:honeybee");
}

#[test]
fn nicknames_leave_the_long_names_alone() {
	assert_eq!(to_unicode("\\:phaistos-disc-sign-bee \\:Bee").as_deref(), Ok("𐇱 𐐒"));
}
