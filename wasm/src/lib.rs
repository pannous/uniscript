//! Uniscript compiled to WebAssembly: the API of the TypeScript port in js/, backed by the Rust reference crate.
//!
//! Results are plain JS objects; offsets (`at`, `start`, `end`, `length`) are UTF-8 byte offsets as in Rust.
//! Errors are thrown as `Error`s named `UniscriptError` with `kind` (`UnknownEntity`, `Unclosed`, `Unsupported`,
//! `InvalidMeta`) and `detail` (the name, rest or content; for `Unsupported` the warning).

use serde::{Deserialize, Serialize};
use uniscript::{Error, MetaRun, Styled, Uniscript, Warning, WarningMode};
use wasm_bindgen::prelude::*;

const ERROR_NAME: &str = "UniscriptError";

thread_local! {
	static CONVERTER: Uniscript<'static> = Uniscript::default();
}

fn with_converter<T>(action: impl FnOnce(&Uniscript<'static>) -> T) -> T {
	CONVERTER.with(action)
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
	let (text, warnings) = with_converter(|converter| converter.convert(source, WarningMode::Warn)).map_err(thrown)?;
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
	let (text, warnings) = with_converter(|converter| converter.convert(source, mode)).map_err(thrown)?;
	Ok(to_js(&Conversion { text, warnings: js_warnings(warnings) }))
}

/// Unicode → uniscript; `toUnicode` gives the text back
#[wasm_bindgen(js_name = toUniscript)]
pub fn to_uniscript(text: &str) -> String {
	with_converter(|converter| converter.to_uniscript(text))
}

/// The header `<:uniscript version="…">` at the start of the source: `{ version, length }`, else undefined
#[wasm_bindgen]
pub fn header(source: &str) -> JsValue {
	uniscript::header(source).map_or(JsValue::UNDEFINED, |found| to_js(&JsHeader { version: found.version, length: found.length }))
}

/// A font style of the entities: `{ name, lang, families, features }`, else undefined
#[wasm_bindgen]
pub fn font(name: &str) -> JsValue {
	with_converter(|converter| {
		converter.font(name).map_or(JsValue::UNDEFINED, |found| to_js(&JsFont { name: found.name, lang: found.lang, families: found.families, features: found.features }))
	})
}

/// The CSS declaration template of a meta key (`color` → `color: {}`), else undefined
#[wasm_bindgen(js_name = metaTemplate)]
pub fn meta_template(key: &str) -> Option<String> {
	with_converter(|converter| converter.meta_template(key).map(str::to_string))
}

/// Tagged text → `{ styled: { text, runs }, warnings }`
#[wasm_bindgen(js_name = metaRuns)]
pub fn meta_runs(tagged: &str) -> JsValue {
	let (styled, warnings) = with_converter(|converter| converter.meta_runs(tagged));
	to_js(&MetaRuns { styled: styled.into(), warnings: js_warnings(warnings) })
}

/// HTML of `styled` (from `metaRuns`): each meta run a `<span>` with its lang and CSS
#[wasm_bindgen]
pub fn html(styled: JsValue) -> Result<String, JsValue> {
	let styled: JsStyled = serde_wasm_bindgen::from_value(styled).map_err(JsValue::from)?;
	Ok(with_converter(|converter| converter.html(&styled.into())))
}
