//! Uniscript compiled to WebAssembly: the API of the TypeScript port in js/, backed by the Rust reference crate.
//!
//! Results are plain JS objects; offsets (`at`, `start`, `end`, `length`) are UTF-8 byte offsets as in Rust.
//! Errors are thrown as `Error`s named `UniscriptError` with `kind` (`UnknownEntity`, `Unclosed`, `Unsupported`,
//! `InvalidMeta`) and `detail` (the name, rest or content; for `Unsupported` the warning).

use serde::{Deserialize, Serialize};
use uniscript::index::Index;
use uniscript::{Error, MetaRun, Styled, Uniscript, Warning, WarningMode};
use std::cell::RefCell;
use wasm_bindgen::prelude::*;

const ERROR_NAME: &str = "UniscriptError";
const NOT_LOADED: &str = "uniscript: no index loaded, await init() first";

thread_local! {
	static CONVERTER: RefCell<Option<Uniscript<'static>>> = const { RefCell::new(None) };
}

fn js_error(message: &str) -> JsValue {
	js_sys::Error::new(message).into()
}

fn install(index: Result<Index<'static>, String>) -> Result<(), JsValue> {
	let converter = Uniscript::new(index.map_err(|error| js_error(&error))?);
	CONVERTER.with(|loaded| loaded.replace(Some(converter)));
	Ok(())
}

fn leaked(bytes: Vec<u8>) -> &'static [u8] {
	Box::leak(bytes.into_boxed_slice())
}

/// Loads the index (the bytes of data/entities.idx): they live as long as the page, a second load replaces the converter
/// and keeps the old bytes
#[wasm_bindgen(js_name = loadIndex)]
pub fn load_index(bytes: Vec<u8>) -> Result<(), JsValue> {
	install(Index::new(leaked(bytes)))
}

/// Loads a chunk manifest (manifest.usxc from `uniscript chunks`) instead of a whole index; its version for cache busting
#[wasm_bindgen(js_name = loadChunkManifest)]
pub fn load_chunk_manifest(bytes: Vec<u8>) -> Result<u32, JsValue> {
	install(Index::chunked(leaked(bytes)))?;
	with_converter(|converter| converter.index().version())
}

/// The chunk of the most used entries, which every lookup needs first (none for a whole index)
#[wasm_bindgen(js_name = commonChunk)]
pub fn common_chunk() -> Result<Option<u32>, JsValue> {
	with_converter(|converter| converter.index().common_chunk().map(|number| number as u32))
}

/// Adds chunk `number` (`<number>.idx` next to the manifest)
#[wasm_bindgen(js_name = addChunk)]
pub fn add_chunk(number: usize, bytes: Vec<u8>) -> Result<(), JsValue> {
	with_converter(|converter| converter.index().add_chunk(number, leaked(bytes)))?.map_err(|error| js_error(&error))
}

/// The chunks converting `text` still needs (empty for a whole index): add them and ask again until none are missing
#[wasm_bindgen(js_name = missingChunks)]
pub fn missing_chunks(text: &str) -> Result<Vec<u32>, JsValue> {
	with_converter(|converter| converter.missing_chunks(text).into_iter().map(|number| number as u32).collect())
}

fn with_converter<T>(action: impl FnOnce(&Uniscript<'static>) -> T) -> Result<T, JsValue> {
	CONVERTER.with(|loaded| loaded.borrow().as_ref().map(action)).ok_or_else(|| js_error(NOT_LOADED))
}

#[derive(Serialize, Deserialize)]
struct JsWarning {
	message: String,
	at: usize,
}

impl From<Warning> for JsWarning {
	fn from(Warning { message, at }: Warning) -> Self {
		JsWarning { message, at }
	}
}

fn js_warnings(warnings: Vec<Warning>) -> Vec<JsWarning> {
	warnings.into_iter().map(JsWarning::from).collect()
}

#[derive(Serialize)]
struct Conversion {
	text: String,
	warnings: Vec<JsWarning>,
}

#[derive(Serialize, Deserialize)]
struct JsMetaRun {
	key: String,
	value: String,
	start: usize,
	end: usize,
	at: usize,
}

#[derive(Serialize, Deserialize)]
struct JsStyled {
	text: String,
	runs: Vec<JsMetaRun>,
}

impl From<Styled> for JsStyled {
	fn from(styled: Styled) -> Self {
		let runs = styled.runs.into_iter().map(|MetaRun { key, value, start, end, at }| JsMetaRun { key, value, start, end, at }).collect();
		JsStyled { text: styled.text, runs }
	}
}

impl From<JsStyled> for Styled {
	fn from(styled: JsStyled) -> Self {
		let runs = styled.runs.into_iter().map(|JsMetaRun { key, value, start, end, at }| MetaRun { key, value, start, end, at }).collect();
		Styled { text: styled.text, runs }
	}
}

#[derive(Serialize)]
struct MetaRuns {
	styled: JsStyled,
	warnings: Vec<JsWarning>,
}

#[derive(Serialize)]
struct JsHeader<'a> {
	version: &'a str,
	length: usize,
}

#[derive(Serialize)]
struct JsFont<'a> {
	name: &'a str,
	lang: &'a str,
	families: Vec<&'a str>,
	features: Vec<&'a str>,
}

fn to_js(value: &impl Serialize) -> JsValue {
	value.serialize(&serde_wasm_bindgen::Serializer::json_compatible()).expect("plain data serializes")
}

fn thrown(error: Error) -> JsValue {
	let (kind, detail) = match &error {
		Error::UnknownEntity(name) => ("UnknownEntity", JsValue::from_str(name)),
		Error::Unclosed(rest) => ("Unclosed", JsValue::from_str(rest)),
		Error::Unsupported(warning) => ("Unsupported", to_js(&JsWarning::from(warning.clone()))),
		Error::InvalidMeta(content) => ("InvalidMeta", JsValue::from_str(content)),
	};
	let js_error = js_sys::Error::new(&error.to_string());
	js_error.set_name(ERROR_NAME);
	let set = |property: &str, value: &JsValue| js_sys::Reflect::set(&js_error, &property.into(), value).expect("an Error is extensible");
	set("kind", &kind.into());
	set("detail", &detail);
	js_error.into()
}

fn warning_mode(mode: Option<String>) -> Result<WarningMode, JsValue> {
	match mode.as_deref() {
		None | Some("warn") => Ok(WarningMode::Warn),
		Some("error") => Ok(WarningMode::Error),
		Some("lenient") => Ok(WarningMode::Lenient),
		Some(other) => Err(JsValue::from(js_sys::TypeError::new(&format!("unknown warning mode {other}: use warn, error or lenient")))),
	}
}

/// The uniscript version this implementation reads; uniscript.js exports it as UNISCRIPT_VERSION
#[wasm_bindgen(js_name = uniscriptVersion)]
pub fn uniscript_version() -> String {
	uniscript::UNISCRIPT_VERSION.to_string()
}

/// Uniscript → Unicode; warnings go to the console
#[wasm_bindgen(js_name = toUnicode)]
pub fn to_unicode(source: &str) -> Result<String, JsValue> {
	let (text, warnings) = with_converter(|converter| converter.convert(source, WarningMode::Warn))?.map_err(thrown)?;
	warnings.iter().for_each(|warning| web_sys_warn(&format!("warning: {warning}")));
	Ok(text)
}

#[wasm_bindgen]
extern "C" {
	#[wasm_bindgen(js_namespace = console, js_name = warn)]
	fn web_sys_warn(message: &str);
}

/// Uniscript → `{ text, warnings }`; mode "warn" (default), "error" (the first warning throws) or "lenient"
/// (errors become warnings, the faulty uniscript stays as written)
#[wasm_bindgen]
pub fn convert(source: &str, mode: Option<String>) -> Result<JsValue, JsValue> {
	let mode = warning_mode(mode)?;
	let (text, warnings) = with_converter(|converter| converter.convert(source, mode))?.map_err(thrown)?;
	Ok(to_js(&Conversion { text, warnings: js_warnings(warnings) }))
}

/// Unicode → uniscript; `toUnicode` gives the text back
#[wasm_bindgen(js_name = toUniscript)]
pub fn to_uniscript(text: &str) -> Result<String, JsValue> {
	with_converter(|converter| converter.to_uniscript(text))
}

/// The header `<:uniscript version="…">` at the start of the source: `{ version, length }`, else undefined
#[wasm_bindgen]
pub fn header(source: &str) -> JsValue {
	uniscript::header(source).map_or(JsValue::UNDEFINED, |found| to_js(&JsHeader { version: found.version, length: found.length }))
}

/// A font style of the entities: `{ name, lang, families, features }`, else undefined
#[wasm_bindgen]
pub fn font(name: &str) -> Result<JsValue, JsValue> {
	with_converter(|converter| {
		converter.font(name).map_or(JsValue::UNDEFINED, |found| to_js(&JsFont { name: found.name, lang: found.lang, families: found.families, features: found.features }))
	})
}

/// The CSS declaration template of a meta key (`color` → `color: {}`), else undefined
#[wasm_bindgen(js_name = metaTemplate)]
pub fn meta_template(key: &str) -> Result<Option<String>, JsValue> {
	with_converter(|converter| converter.meta_template(key).map(str::to_string))
}

/// Tagged text → `{ styled: { text, runs }, warnings }`
#[wasm_bindgen(js_name = metaRuns)]
pub fn meta_runs(tagged: &str) -> Result<JsValue, JsValue> {
	let (styled, warnings) = with_converter(|converter| converter.meta_runs(tagged))?;
	Ok(to_js(&MetaRuns { styled: styled.into(), warnings: js_warnings(warnings) }))
}

/// HTML of `styled` (from `metaRuns`): each meta run a `<span>` with its lang and CSS
#[wasm_bindgen]
pub fn html(styled: JsValue) -> Result<String, JsValue> {
	let styled: JsStyled = serde_wasm_bindgen::from_value(styled).map_err(JsValue::from)?;
	with_converter(|converter| converter.html(&styled.into()))
}
