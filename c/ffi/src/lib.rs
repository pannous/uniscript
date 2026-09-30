//! The C ABI of the uniscript crate, declared in c/uniscript.h. Strings cross as NUL-terminated UTF-8 allocated with
//! the C allocator, so the caller frees them with `uniscript_free` (= free) and the structs with their `*_free`.

use std::ffi::{c_char, c_int, c_void, CStr};
use std::ptr::null_mut;
use uniscript::{Error, MetaRun, Uniscript, Warning, WarningMode};

extern "C" {
	fn malloc(size: usize) -> *mut c_void;
	fn free(pointer: *mut c_void);
}

thread_local! {
	static CONVERTER: Uniscript<'static> = Uniscript::default();
}

#[repr(C)]
#[derive(Clone, Copy)]
pub enum Mode {
	Warn,
	Error,
	Lenient,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub enum ErrorKind {
	Ok,
	UnknownEntity,
	Unclosed,
	Unsupported,
	InvalidMeta,
	InvalidInput,
}

#[repr(C)]
pub struct CWarning {
	message: *mut c_char,
	at: usize,
}

#[repr(C)]
pub struct CResult {
	text: *mut c_char,
	error_kind: ErrorKind,
	error: *mut c_char,
	error_detail: *mut c_char,
	error_at: usize,
	warnings: *mut CWarning,
	warning_count: usize,
}

#[repr(C)]
pub struct CMetaRun {
	key: *mut c_char,
	value: *mut c_char,
	start: usize,
	end: usize,
	at: usize,
}

#[repr(C)]
pub struct CStyled {
	text: *mut c_char,
	runs: *mut CMetaRun,
	run_count: usize,
	warnings: *mut CWarning,
	warning_count: usize,
}

#[repr(C)]
pub struct CFont {
	name: *mut c_char,
	lang: *mut c_char,
	families: *mut *mut c_char,
	family_count: usize,
	features: *mut *mut c_char,
	feature_count: usize,
}

/// A copy of the string on the C heap, NUL-terminated
fn owned(text: &str) -> *mut c_char {
	unsafe {
		let copy = malloc(text.len() + 1) as *mut u8;
		std::ptr::copy_nonoverlapping(text.as_ptr(), copy, text.len());
		*copy.add(text.len()) = 0;
		copy as *mut c_char
	}
}

/// A C array of the items; null when empty
fn owned_array<T, C>(items: &[T], convert: impl Fn(&T) -> C) -> *mut C {
	if items.is_empty() {
		return null_mut();
	}
	unsafe {
		let array = malloc(items.len() * std::mem::size_of::<C>()) as *mut C;
		items.iter().enumerate().for_each(|(i, item)| array.add(i).write(convert(item)));
		array
	}
}

unsafe fn free_array<C>(array: *mut C, count: usize, free_item: impl Fn(&mut C)) {
	if !array.is_null() {
		(0..count).for_each(|i| free_item(&mut *array.add(i)));
		free(array as *mut c_void);
	}
}

/// The UTF-8 text of a C string; None for NULL or invalid UTF-8
unsafe fn text<'a>(pointer: *const c_char) -> Option<&'a str> {
	(!pointer.is_null()).then(|| CStr::from_ptr(pointer).to_str().ok()).flatten()
}

fn warnings(warnings: &[Warning]) -> (*mut CWarning, usize) {
	(owned_array(warnings, |warning| CWarning { message: owned(&warning.message), at: warning.at }), warnings.len())
}

fn success(text: &str, found: &[Warning]) -> CResult {
	let (warnings, warning_count) = warnings(found);
	CResult { text: owned(text), warnings, warning_count, ..cleared() }
}

fn cleared() -> CResult {
	CResult { text: null_mut(), error_kind: ErrorKind::Ok, error: null_mut(), error_detail: null_mut(), error_at: 0, warnings: null_mut(), warning_count: 0 }
}

fn failure(error_kind: ErrorKind, error: &str, detail: &str, error_at: usize) -> CResult {
	CResult { error_kind, error: owned(error), error_detail: owned(detail), error_at, ..cleared() }
}

fn error_result(error: &Error) -> CResult {
	let message = error.to_string();
	match error {
		Error::UnknownEntity(name) => failure(ErrorKind::UnknownEntity, &message, name, 0),
		Error::Unclosed(rest) => failure(ErrorKind::Unclosed, &message, rest, 0),
		Error::Unsupported(warning) => failure(ErrorKind::Unsupported, &message, &warning.message, warning.at),
		Error::InvalidMeta(content) => failure(ErrorKind::InvalidMeta, &message, content, 0),
	}
}

fn invalid_input() -> CResult {
	failure(ErrorKind::InvalidInput, "uniscript: invalid input (NULL or not UTF-8)", "", 0)
}

fn warning_mode(mode: Mode) -> WarningMode {
	match mode {
		Mode::Warn => WarningMode::Warn,
		Mode::Error => WarningMode::Error,
		Mode::Lenient => WarningMode::Lenient,
	}
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_convert(source: *const c_char, mode: Mode) -> CResult {
	let Some(source) = text(source) else { return invalid_input() };
	match CONVERTER.with(|converter| converter.convert(source, warning_mode(mode))) {
		Ok((text, warnings)) => success(&text, &warnings),
		Err(error) => error_result(&error),
	}
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_to_unicode(source: *const c_char) -> *mut c_char {
	text(source).and_then(|source| uniscript::to_unicode(source).ok()).map_or(null_mut(), |text| owned(&text))
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_to_uniscript(text_pointer: *const c_char) -> *mut c_char {
	text(text_pointer).map_or(null_mut(), |text| owned(&CONVERTER.with(|converter| converter.to_uniscript(text))))
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_header(source: *const c_char, version: *mut *const c_char, version_length: *mut usize, length: *mut usize) -> c_int {
	let Some(header) = text(source).and_then(uniscript::header) else { return 0 };
	if !version.is_null() {
		*version = header.version.as_ptr() as *const c_char;
	}
	if !version_length.is_null() {
		*version_length = header.version.len();
	}
	if !length.is_null() {
		*length = header.length;
	}
	1
}

fn meta_run(run: &MetaRun) -> CMetaRun {
	CMetaRun { key: owned(&run.key), value: owned(&run.value), start: run.start, end: run.end, at: run.at }
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_meta_runs(tagged: *const c_char) -> CStyled {
	let (styled, found) = CONVERTER.with(|converter| converter.meta_runs(text(tagged).unwrap_or("")));
	let (warnings, warning_count) = warnings(&found);
	CStyled { text: owned(&styled.text), runs: owned_array(&styled.runs, meta_run), run_count: styled.runs.len(), warnings, warning_count }
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_html(tagged: *const c_char) -> CResult {
	let Some(tagged) = text(tagged) else { return invalid_input() };
	CONVERTER.with(|converter| {
		let (styled, warnings) = converter.meta_runs(tagged);
		success(&converter.html(&styled), &warnings)
	})
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_font_lookup(name: *const c_char, font: *mut CFont) -> c_int {
	let Some(found) = text(name).and_then(|name| CONVERTER.with(|converter| converter.font(name))) else { return 0 };
	if !font.is_null() {
		let strings = |items: &[&str]| owned_array(items, |item| owned(item));
		*font = CFont {
			name: owned(found.name),
			lang: owned(found.lang),
			families: strings(&found.families),
			family_count: found.families.len(),
			features: strings(&found.features),
			feature_count: found.features.len(),
		};
	}
	1
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_meta_template(key: *const c_char) -> *mut c_char {
	text(key).and_then(|key| CONVERTER.with(|converter| converter.meta_template(key))).map_or(null_mut(), owned)
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_free(text: *mut c_char) {
	free(text as *mut c_void);
}

unsafe fn free_warnings(warnings: *mut CWarning, count: usize) {
	free_array(warnings, count, |warning| uniscript_free(warning.message));
}

unsafe fn free_strings(strings: *mut *mut c_char, count: usize) {
	free_array(strings, count, |string| uniscript_free(*string));
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_result_free(result: *mut CResult) {
	let Some(result) = result.as_mut() else { return };
	[result.text, result.error, result.error_detail].into_iter().for_each(|text| uniscript_free(text));
	free_warnings(result.warnings, result.warning_count);
	*result = cleared();
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_styled_free(styled: *mut CStyled) {
	let Some(styled) = styled.as_mut() else { return };
	uniscript_free(styled.text);
	free_array(styled.runs, styled.run_count, |run| [run.key, run.value].into_iter().for_each(|text| uniscript_free(text)));
	free_warnings(styled.warnings, styled.warning_count);
	*styled = CStyled { text: null_mut(), runs: null_mut(), run_count: 0, warnings: null_mut(), warning_count: 0 };
}

#[no_mangle]
pub unsafe extern "C" fn uniscript_font_free(font: *mut CFont) {
	let Some(font) = font.as_mut() else { return };
	[font.name, font.lang].into_iter().for_each(|text| uniscript_free(text));
	free_strings(font.families, font.family_count);
	free_strings(font.features, font.feature_count);
	*font = CFont { name: null_mut(), lang: null_mut(), families: null_mut(), family_count: 0, features: null_mut(), feature_count: 0 };
}
