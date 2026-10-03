//! One test crate for all tests: every tests/*.rs file is a module, so cargo links one test binary instead of one per file.
//! Run one file with `cargo test --test tests <file_stem>::`.

mod block_readings_test;
mod chinese_test;
mod chunks_test;
mod cli_file_test;
mod code_points_test;
mod entity_names_test;
mod inline_tags_test;
mod lenient_test;
mod local_entities_test;
mod meta_test;
mod runtime_index_test;
mod styles_test;
mod uniscript_test;
