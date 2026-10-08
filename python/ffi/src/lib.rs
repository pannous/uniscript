//! The Rust converter behind the Python package `uniscript`: plain tuples in and out, `uniscript/__init__.py` wraps
//! them in the dataclasses and exceptions shared with the native Python package.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::sync::{Arc, Mutex};
use uniscript::index::{self, Index, Table, TABLES};
use uniscript::{Error, Meta, MetaRun, Styled, Uniscript, Warning, WarningMode, ENTITIES_INDEX};

type WarningTuple = (String, usize);
type RunTuple = (String, String, usize, usize, usize);
/// kind (`UnknownEntity`, `Unclosed`, `Unsupported`, `InvalidMeta`), payload, and the warning of `Unsupported`
type ErrorTuple = (&'static str, String, Option<WarningTuple>);
type Entry = (String, String);

fn warning_tuple(warning: Warning) -> WarningTuple {
	(warning.message, warning.at)
}

fn warning_tuples(warnings: Vec<Warning>) -> Vec<WarningTuple> {
	warnings.into_iter().map(warning_tuple).collect()
}

fn error_tuple(error: Error) -> ErrorTuple {
	match error {
		Error::UnknownEntity(name) => ("UnknownEntity", name, None),
		Error::Unclosed(rest) => ("Unclosed", rest, None),
		Error::Unsupported(warning) => ("Unsupported", warning.message.clone(), Some(warning_tuple(warning))),
		Error::InvalidMeta(content) => ("InvalidMeta", content, None),
	}
}

fn warning_mode(name: &str) -> PyResult<WarningMode> {
	match name {
		"warn" => Ok(WarningMode::Warn),
		"error" => Ok(WarningMode::Error),
		"lenient" => Ok(WarningMode::Lenient),
		_ => Err(PyValueError::new_err(format!("unknown warning mode {name}"))),
	}
}

fn table(number: usize) -> PyResult<Table> {
	TABLES.get(number).copied().ok_or_else(|| PyValueError::new_err(format!("no index table {number}")))
}

fn owned(entry: (&str, &str)) -> Entry {
	(entry.0.to_string(), entry.1.to_string())
}

/// The bytes of a USX1 index: the built-in one, or checked bytes of another
#[derive(Clone)]
enum Bytes {
	BuiltIn,
	Owned(Arc<[u8]>),
}

impl Bytes {
	fn data(&self) -> &[u8] {
		match self {
			Bytes::BuiltIn => ENTITIES_INDEX,
			Bytes::Owned(bytes) => bytes,
		}
	}

	fn index(&self) -> Index<'_> {
		Index::new(self.data()).expect("checked when the bytes were loaded")
	}
}

/// An entity index; lookups read its bytes in place
#[pyclass(frozen, name = "Index")]
struct PyIndex {
	bytes: Bytes,
}

#[pymethods]
impl PyIndex {
	#[new]
	#[pyo3(signature = (data=None))]
	fn new(data: Option<Vec<u8>>) -> PyResult<Self> {
		let Some(data) = data else { return Ok(PyIndex { bytes: Bytes::BuiltIn }) };
		Index::new(&data).map_err(PyValueError::new_err)?;
		Ok(PyIndex { bytes: Bytes::Owned(data.into()) })
	}

	#[getter]
	fn data(&self) -> &[u8] {
		self.bytes.data()
	}

	fn count(&self, table_number: usize) -> PyResult<usize> {
		Ok(self.bytes.index().len(table(table_number)?))
	}

	fn get(&self, table_number: usize, key: &str) -> PyResult<Option<String>> {
		Ok(self.bytes.index().get(table(table_number)?, key).map(str::to_string))
	}

	fn entry(&self, table_number: usize, key: &str) -> PyResult<Option<Entry>> {
		Ok(self.bytes.index().entry(table(table_number)?, key).map(owned))
	}

	fn entries(&self, table_number: usize) -> PyResult<Vec<Entry>> {
		Ok(self.bytes.index().entries(table(table_number)?).map(owned).collect())
	}
}

/// A converter over one index
#[pyclass(frozen)]
struct Converter {
	// declared before `_bytes`, so it is dropped before the bytes it borrows
	converter: Mutex<Uniscript<'static>>,
	_bytes: Bytes,
}

#[pymethods]
impl Converter {
	#[new]
	fn new(index: &PyIndex) -> Self {
		let bytes = index.bytes.clone();
		// SAFETY: the bytes are static or shared through the Arc in `_bytes`, which outlives the converter
		let data: &'static [u8] = unsafe { std::slice::from_raw_parts(bytes.data().as_ptr(), bytes.data().len()) };
		let converter = Uniscript::new(Index::new(data).expect("checked when the bytes were loaded"));
		Converter { converter: Mutex::new(converter), _bytes: bytes }
	}

	/// (text, warnings, None) or (None, [], error)
	fn convert(&self, source: &str, mode: &str) -> PyResult<(Option<String>, Vec<WarningTuple>, Option<ErrorTuple>)> {
		let mode = warning_mode(mode)?;
		Ok(match self.converter.lock().expect("converter lock").convert(source, mode) {
			Ok((text, warnings)) => (Some(text), warning_tuples(warnings), None),
			Err(error) => (None, Vec::new(), Some(error_tuple(error))),
		})
	}

	fn to_uniscript(&self, text: &str) -> String {
		self.converter.lock().expect("converter lock").to_uniscript(text)
	}

	fn explicit(&self, source: &str) -> String {
		self.converter.lock().expect("converter lock").explicit(source)
	}

	/// (name, lang, families, features)
	fn font(&self, name: &str) -> Option<(String, String, Vec<String>, Vec<String>)> {
		let converter = self.converter.lock().expect("converter lock");
		let strings = |items: Vec<&str>| items.into_iter().map(str::to_string).collect();
		converter.font(name).map(|font| (font.name.to_string(), font.lang.to_string(), strings(font.families), strings(font.features)))
	}

	fn meta_template(&self, key: &str) -> Option<String> {
		self.converter.lock().expect("converter lock").meta_template(key).map(str::to_string)
	}

	/// (plain text, runs, warnings)
	fn meta_runs(&self, tagged: &str) -> (String, Vec<RunTuple>, Vec<WarningTuple>) {
		let (styled, warnings) = self.converter.lock().expect("converter lock").meta_runs(tagged);
		let runs = styled.runs.into_iter().map(|run| (run.key, run.value, run.start, run.end, run.at)).collect();
		(styled.text, runs, warning_tuples(warnings))
	}

	fn html(&self, text: String, runs: Vec<RunTuple>) -> String {
		let runs = runs.into_iter().map(|(key, value, start, end, at)| MetaRun { key, value, start, end, at }).collect();
		self.converter.lock().expect("converter lock").html(&Styled { text, runs })
	}
}

/// (version, length) of the header at the start of the source
#[pyfunction]
fn header(source: &str) -> Option<(String, usize)> {
	uniscript::header(source).map(|header| (header.version.to_string(), header.length))
}

/// Uniscript with every character beyond ASCII written by its code point (`\:U+E000`)
#[pyfunction]
fn ascii_escaped(uniscript: &str) -> String {
	uniscript::ascii_escaped(uniscript)
}

/// Whether a header version is read without warning: none, or https://uniscript.org/vN for any number N
#[pyfunction]
fn reads_version(version: &str) -> bool {
	uniscript::reads_version(version)
}

fn meta(kind: &str, key: String, value: String) -> PyResult<Meta> {
	match kind {
		"open" => Ok(Meta::Open { key, value }),
		"close" => Ok(Meta::Close { key }),
		"attached" => Ok(Meta::Attached { key, value }),
		_ => Err(PyValueError::new_err(format!("unknown meta kind {kind}"))),
	}
}

fn meta_tuple(meta: Meta) -> (&'static str, String, String) {
	match meta {
		Meta::Open { key, value } => ("open", key, value),
		Meta::Close { key } => ("close", key, String::new()),
		Meta::Attached { key, value } => ("attached", key, value),
	}
}

/// The TAG sequence of a meta: kind `open`, `close` or `attached`
#[pyfunction]
fn meta_tags(kind: &str, key: String, value: String) -> PyResult<String> {
	Ok(meta(kind, key, value)?.tags())
}

/// The uniscript of a meta: `<:font han-japanese>`, `<:/font>`, `color red`
#[pyfunction]
fn meta_uniscript(kind: &str, key: String, value: String) -> PyResult<String> {
	Ok(meta(kind, key, value)?.uniscript())
}

/// (kind, key, value) of the meta sequence at the start of the text and its byte length
#[pyfunction]
fn meta_at(text: &str) -> Option<((&'static str, String, String), usize)> {
	uniscript::meta::meta_at(text).map(|(meta, length)| (meta_tuple(meta), length))
}

#[pyfunction]
fn text_hash(text: &str) -> u32 {
	index::text_hash(text)
}

#[pymodule]
fn _uniscript(module: &Bound<'_, PyModule>) -> PyResult<()> {
	module.add_class::<PyIndex>()?;
	module.add_class::<Converter>()?;
	module.add_function(wrap_pyfunction!(header, module)?)?;
	module.add_function(wrap_pyfunction!(reads_version, module)?)?;
	module.add_function(wrap_pyfunction!(ascii_escaped, module)?)?;
	module.add_function(wrap_pyfunction!(meta_tags, module)?)?;
	module.add_function(wrap_pyfunction!(meta_uniscript, module)?)?;
	module.add_function(wrap_pyfunction!(meta_at, module)?)?;
	module.add_function(wrap_pyfunction!(text_hash, module)?)?;
	module.add("UNISCRIPT_VERSION", uniscript::UNISCRIPT_VERSION)?;
	Ok(())
}
