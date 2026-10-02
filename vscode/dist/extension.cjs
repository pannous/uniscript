"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/extension.ts
var extension_exports = {};
__export(extension_exports, {
  activate: () => activate,
  deactivate: () => deactivate
});
module.exports = __toCommonJS(extension_exports);
var vscode = __toESM(require("vscode"), 1);
var import_node_fs = require("node:fs");

// ../js/src/entityIndex.ts
var MAGIC = "USX1";
var HASH_MULTIPLIER = 31;
var RECORD_SIZE = 20;
var HEADER_FIXED = 8;
var TABLE_ENTRY_SIZE = 8;
var Table = {
  /** name → text; a block entry is `block operand` (`fracture A`, `red *suffix`), a block itself `block ` → "" */
  names: 0,
  /** a non-ASCII character → its preferred uniscript */
  chars: 1,
  /** a suffix control → its block type */
  suffixes: 2,
  /** a font style → "", `style field` → value (`cuneiform-hittite lang` → hit-Xsux) */
  fonts: 3,
  /** a meta key → its CSS declaration, `{}` the value (`color` → `color: {}`) */
  meta: 4
};
var TABLES = Object.values(Table);
var NODE_FILE_SYSTEM = "node:fs/promises";
var isNode = () => !!globalThis.process?.versions?.node;
var encoder = new TextEncoder();
var decoder = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });
function textHash(text, multiplier = HASH_MULTIPLIER) {
  const bytes = typeof text === "string" ? encoder.encode(text) : text;
  return bytes.reduce((hash, byte) => Math.imul(hash, multiplier) + byte >>> 0, 0);
}
async function readBytes(source) {
  const url = source instanceof URL ? source : void 0;
  if (isNode() && (!url || url.protocol === "file:")) {
    const { readFile } = await import(NODE_FILE_SYSTEM);
    return readFile(source);
  }
  const response = await fetch(source);
  if (!response.ok) throw new Error(`uniscript index ${source}: HTTP ${response.status}`);
  return new Uint8Array(await response.arrayBuffer());
}
var EntityIndex = class _EntityIndex {
  #bytes;
  #view;
  constructor(data) {
    this.#bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
    this.#view = new DataView(this.#bytes.buffer, this.#bytes.byteOffset, this.#bytes.byteLength);
    if (this.#bytes.length < HEADER_FIXED || decoder.decode(this.#bytes.subarray(0, 4)) !== MAGIC) {
      throw new Error("not a uniscript index (magic USX1 missing)");
    }
    if (this.#u32(4) < TABLES.length) throw new Error("uniscript index has too few tables");
  }
  /** The index at a file path (Node) or URL (fetch in browsers and Node) */
  static async load(source) {
    return new _EntityIndex(await readBytes(source));
  }
  #u32(offset) {
    return this.#view.getUint32(offset, true);
  }
  #tableStart(table) {
    return this.#u32(HEADER_FIXED + TABLE_ENTRY_SIZE * table);
  }
  count(table) {
    return this.#u32(HEADER_FIXED + TABLE_ENTRY_SIZE * table + 4);
  }
  #record(table, position) {
    const at = this.#tableStart(table) + position * RECORD_SIZE;
    const field = (n) => this.#u32(at + 4 * n);
    return { hash: field(0), keyOffset: field(1), keyLength: field(2), valueOffset: field(3), valueLength: field(4) };
  }
  #text(offset, length) {
    return decoder.decode(this.#bytes.subarray(offset, offset + length));
  }
  #keyEquals(record, key) {
    if (record.keyLength !== key.length) return false;
    return key.every((byte, i) => this.#bytes[record.keyOffset + i] === byte);
  }
  /** Binary search for the first record of the key's hash, then compare keys (hashes may collide) */
  get(table, key) {
    return this.entry(table, key)?.[1];
  }
  /** The stored key and its value */
  entry(table, key) {
    const keyBytes = encoder.encode(key);
    const wanted = textHash(keyBytes);
    const count = this.count(table);
    let [low, high] = [0, count];
    while (low < high) {
      const middle = low + high >>> 1;
      if (this.#record(table, middle).hash < wanted) low = middle + 1;
      else high = middle;
    }
    for (let position = low; position < count; position++) {
      const record = this.#record(table, position);
      if (record.hash !== wanted) return void 0;
      if (this.#keyEquals(record, keyBytes)) return [key, this.#text(record.valueOffset, record.valueLength)];
    }
    return void 0;
  }
  /** All key, value pairs of a table, in index order */
  *entries(table) {
    for (let position = 0; position < this.count(table); position++) {
      const record = this.#record(table, position);
      yield [this.#text(record.keyOffset, record.keyLength), this.#text(record.valueOffset, record.valueLength)];
    }
  }
};

// ../js/src/meta.ts
var CANCEL_TAG = "\u{E007F}";
var TAG_BASE = 917504;
var TAG_TEXT_FIRST = 917536;
var TAG_TEXT_LAST = 917630;
var OPEN_SIGIL = "<";
var CLOSE_SIGIL = "</";
var ATTACH_SIGIL = ":";
var VALUE_PUNCTUATION = "#.%+-_,()/";
var ZERO_WIDTH_JOINER = 8205;
var EMOJI_PRESENTATION = 65039;
var EXTENDING_RANGES = [
  [768, 879],
  [6832, 6911],
  [7616, 7679],
  [8400, 8447],
  [65024, 65039],
  [65056, 65071],
  [8205, 8205],
  [78896, 78943],
  [127995, 127999],
  [917504, 917631],
  [917760, 917999]
];
var HIEROGLYPH_JOINERS = [78896, 78902];
var encoder2 = new TextEncoder();
var decoder2 = new TextDecoder("utf-8", { ignoreBOM: true });
function utf8Length(text) {
  let length = 0;
  for (let i = 0; i < text.length; i++) {
    const unit = text.charCodeAt(i);
    if (unit < 128) length += 1;
    else if (unit < 2048) length += 2;
    else if (unit >= 55296 && unit <= 56319) {
      length += 4;
      i++;
    } else length += 3;
  }
  return length;
}
var within = (code, [first, last]) => code >= first && code <= last;
var isAsciiAlphanumeric = (character) => /^[A-Za-z0-9]$/.test(character);
var Meta = class _Meta {
  kind;
  key;
  /** "" for a close */
  value;
  constructor(kind, key, value = "") {
    this.kind = kind;
    this.key = key;
    this.value = value;
  }
  static open(key, value) {
    return new _Meta("open", key, value);
  }
  static close(key) {
    return new _Meta("close", key);
  }
  static attached(key, value) {
    return new _Meta("attached", key, value);
  }
  #spelled() {
    if (this.kind === "close") return `${CLOSE_SIGIL}${this.key}`;
    return `${this.kind === "open" ? OPEN_SIGIL : ATTACH_SIGIL}${this.key} ${this.value}`;
  }
  /** The TAG sequence: `:color red` → U+E003A U+E0063 … U+E007F */
  tags() {
    return [...this.#spelled()].map((c) => String.fromCodePoint(TAG_BASE + c.codePointAt(0))).join("") + CANCEL_TAG;
  }
  /** The uniscript of a span sequence (`<:font han-japanese>`, `<:/font>`); an attached one is `key value` */
  uniscript() {
    switch (this.kind) {
      case "open":
        return `<:${this.key} ${this.value}>`;
      case "close":
        return `<:/${this.key}>`;
      case "attached":
        return `${this.key} ${this.value}`;
    }
  }
  static parse(spelled) {
    if (spelled.startsWith(CLOSE_SIGIL)) {
      const key2 = spelled.slice(CLOSE_SIGIL.length);
      return isKey(key2) ? _Meta.close(key2) : void 0;
    }
    const space = spelled.indexOf(" ", 1);
    if (spelled.length === 0 || space < 0) return void 0;
    const [key, value] = [spelled.slice(1, space), spelled.slice(space + 1)];
    if (!isKey(key) || !isMetaValue(value)) return void 0;
    if (spelled[0] === OPEN_SIGIL) return _Meta.open(key, value);
    if (spelled[0] === ATTACH_SIGIL) return _Meta.attached(key, value);
    return void 0;
  }
};
function isKey(key) {
  return /^[a-z][a-z0-9-]*$/.test(key);
}
function isMetaValue(value) {
  return value.length > 0 && [...value].every((c) => isAsciiAlphanumeric(c) || VALUE_PUNCTUATION.includes(c));
}
function tagSequenceAt(text, position) {
  let spelled = "";
  for (let at = position; at < text.length; ) {
    const code = text.codePointAt(at);
    const width = code > 65535 ? 2 : 1;
    if (code === 917631) return spelled ? { spelled, length: at + width - position } : void 0;
    if (code < TAG_TEXT_FIRST || code > TAG_TEXT_LAST) return void 0;
    spelled += String.fromCharCode(code - TAG_BASE);
    at += width;
  }
  return void 0;
}
function metaAt(text, position = 0) {
  const sequence = tagSequenceAt(text, position);
  const meta = sequence && Meta.parse(sequence.spelled);
  return meta && { meta, length: sequence.length };
}
function emojiTagsAt(text, position = 0) {
  const sequence = tagSequenceAt(text, position);
  return sequence && [...sequence.spelled].every(isAsciiAlphanumeric) ? sequence.length : void 0;
}
function joinedPrefixes(text, position = 0) {
  const ends = [];
  let at = position;
  const takes = (wanted) => {
    const code = text.codePointAt(at);
    if (code === void 0 || !wanted(code)) return false;
    at += code > 65535 ? 2 : 1;
    return true;
  };
  let joined = takes((code) => code === ZERO_WIDTH_JOINER);
  while (takes((code) => code !== ZERO_WIDTH_JOINER)) {
    takes((code) => code === EMOJI_PRESENTATION);
    if (joined) ends.push(at - position);
    joined = takes((code) => code === ZERO_WIDTH_JOINER);
    if (!joined) break;
  }
  return ends.reverse();
}
function afterBase(text, suffixes) {
  const joiner = text.indexOf(String.fromCodePoint(ZERO_WIDTH_JOINER));
  return joiner < 0 ? text + suffixes : text.slice(0, joiner) + suffixes + text.slice(joiner);
}
function extendsPrevious(previous, code) {
  if (previous !== void 0 && (previous === ZERO_WIDTH_JOINER || within(previous, HIEROGLYPH_JOINERS))) return true;
  return EXTENDING_RANGES.some((range) => within(code, range));
}
function attach(text, sequences) {
  let out = "";
  let previous;
  for (const character of text) {
    const code = character.codePointAt(0);
    if (previous !== void 0 && !extendsPrevious(previous, code)) out += sequences;
    out += character;
    previous = code;
  }
  return out + sequences;
}
var Styled = class _Styled {
  text;
  runs;
  constructor(text, runs) {
    this.text = text;
    this.runs = runs;
  }
  /** Reads the meta sequences out of tagged text. A span closing over spans opened after it closes them too and
   * reopens them, so runs always nest; a close without its open is a warning. */
  static parse(tagged) {
    let text = "";
    let textBytes = 0;
    let runs = [];
    const warnings = [];
    const open = [];
    let clusterStart = 0;
    let previous;
    let at = 0;
    for (let position = 0; position < tagged.length; ) {
      const found = metaAt(tagged, position);
      if (!found) {
        const code = tagged.codePointAt(position);
        const character = String.fromCodePoint(code);
        if (!extendsPrevious(previous, code)) clusterStart = textBytes;
        text += character;
        textBytes += utf8Length(character);
        at += utf8Length(character);
        previous = code;
        position += character.length;
        continue;
      }
      const { meta, length } = found;
      const here = textBytes;
      const { key, value } = meta;
      if (meta.kind === "open") {
        open.push(runs.length);
        runs.push({ key, value, start: here, end: here, at });
      } else if (meta.kind === "attached") {
        runs.push({ key, value, start: clusterStart, end: here, at });
      } else {
        const matching = open.findLastIndex((run) => runs[run].key === key);
        if (matching < 0) warnings.push({ message: `</${key} closes no open ${key}`, at });
        else {
          const closed = open.splice(matching);
          closed.forEach((run) => runs[run].end = here);
          for (const run of closed.slice(1)) {
            open.push(runs.length);
            runs.push({ ...runs[run], start: here, at });
          }
        }
      }
      at += utf8Length(tagged.slice(position, position + length));
      position += length;
    }
    open.forEach((run) => runs[run].end = textBytes);
    runs = runs.filter((run) => run.start < run.end);
    runs.sort((a, b) => a.start - b.start || b.end - a.end);
    return { styled: new _Styled(text, runs), warnings };
  }
  /** The text with `open(run)` before each run and `close` after it, `escape` applied to the text */
  interleaved(open, close, escape) {
    const bytes = encoder2.encode(this.text);
    let out = "";
    let cursor = 0;
    const enclosing = [];
    const advance = (to) => {
      out += escape(decoder2.decode(bytes.subarray(cursor, to)));
      cursor = to;
    };
    const closeUntil = (done) => {
      while (enclosing.length && done(enclosing.at(-1))) {
        advance(enclosing.pop().end);
        out += close;
      }
    };
    for (const run of this.runs) {
      closeUntil((inner) => inner.end <= run.start);
      advance(run.start);
      out += open(run);
      enclosing.push(run);
    }
    closeUntil(() => true);
    advance(bytes.length);
    return out;
  }
};
function escapeHTML(text) {
  return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}
function list(text) {
  return text.split(",").map((item) => item.trim()).filter((item) => item.length > 0);
}

// ../js/src/chunkFetcher.js
var encoder3 = new TextEncoder();
var latin1 = new TextDecoder("latin1");

// ../js/src/core.ts
var MARKER_COLON = ":";
var TAG_OPEN = "<";
var SHORT_OPEN = "\\";
var TAG_CLOSE = ">";
var CLOSING_SLASH = "/";
var ESCAPED_COLON = "<::>";
var ESCAPED_UNICODE = "<:U>";
var SUFFIX_KEY = "*suffix";
var GROUP_KEY = "*group";
var MAX_OPERAND_WORDS = 8;
var META_FALLBACK_KEY = "*meta";
var FONT_KEY = "font";
var LANG_KEY = "lang";
var VALUE_PLACEHOLDER = "{}";
var READ_VERSION = /^https:\/\/uniscript\.org\/v[0-9]+$/;
var readsVersion = (version) => version === "" || READ_VERSION.test(version);
var HEADER_OPEN = "<:uniscript";
var VERSION_ATTRIBUTE = 'version="';
var ATTRIBUTE_QUOTE = '"';
var LINE_BREAKS = ["\r\n", "\n"];
var CODE_POINT = /^(?:(?:[Uu]\+?|0[xX])([0-9A-Fa-f]{1,8})|([0-9A-Fa-f]{4,8}))$/;
var UNICODE_ESCAPE = /U([0-9A-Fa-f]{4,8})(?![A-Za-z0-9_-])/y;
var NAME_TOKEN = /(?:[Uu]\+)?[A-Za-z0-9_-]*/y;
var MARKERS = /<:|\\:|\\(?=U[0-9A-Fa-f]{4,8}(?![A-Za-z0-9_-]))/g;
var MAX_CODE_POINT = 1114111;
var SURROGATES = [55296, 57343];
var WHITESPACE_ENDED_PIECES = /\S*\s|\S+$/gu;
function describeWarning(warning) {
  return `uniscript: ${warning.message} at byte ${warning.at}`;
}
function errorMessage(kind, detail) {
  switch (kind) {
    case "UnknownEntity":
      return `unknown uniscript entity: ${detail}`;
    case "Unclosed":
      return `unclosed <: at ${detail}`;
    case "Unsupported":
      return describeWarning(detail);
    case "InvalidMeta":
      return `invalid meta value in <:${detail}>`;
  }
}
var UniscriptError = class extends Error {
  kind;
  detail;
  constructor(kind, detail) {
    super(errorMessage(kind, detail));
    this.name = "UniscriptError";
    this.kind = kind;
    this.detail = detail;
  }
};
function headerOf(source) {
  if (!source.startsWith(HEADER_OPEN)) return void 0;
  const rest = source.slice(HEADER_OPEN.length);
  if (!rest.startsWith(" ") && !rest.startsWith(TAG_CLOSE)) return void 0;
  const close = rest.indexOf(TAG_CLOSE);
  if (close < 0) return void 0;
  const attributes = rest.slice(0, close);
  const versionAt = attributes.indexOf(VERSION_ATTRIBUTE);
  const version = versionAt < 0 ? "" : attributes.slice(versionAt + VERSION_ATTRIBUTE.length).split(ATTRIBUTE_QUOTE)[0];
  const end = HEADER_OPEN.length + close + 1;
  const lineBreak = LINE_BREAKS.find((lineBreak2) => source.startsWith(lineBreak2, end)) ?? "";
  return { version, end: end + lineBreak.length };
}
function scriptOf(character) {
  const code = character.codePointAt(0) ?? 0;
  if (code >= 77824 && code <= 81919) return "egyptian";
  if (code >= 11904 && code <= 40959 || code >= 131072 && code <= 212991) return "cjk";
  return "";
}
var isNameCharacter = (character) => /^[A-Za-z0-9_-]$/.test(character);
function matchAt(pattern, text, position) {
  pattern.lastIndex = position;
  return pattern.exec(text);
}
function codePointValue(token) {
  const digits = CODE_POINT.exec(token);
  return digits ? parseInt(digits[1] ?? digits[2], 16) : void 0;
}
var unicodeEscapeAt = (text, position) => matchAt(UNICODE_ESCAPE, text, position)?.[1];
function permutations(parts) {
  if (parts.length <= 1) return [parts];
  return parts.flatMap((first, position) => permutations(parts.filter((_, other) => other !== position)).map((order) => [first, ...order]));
}
var characterCount = (text) => [...text].length;
var isClosing = (content) => content === "" || content.startsWith(CLOSING_SLASH);
function splitOnce(text, separator) {
  const at = text.indexOf(separator);
  return at < 0 ? void 0 : [text.slice(0, at), text.slice(at + separator.length)];
}
var words = (text) => text.split(" ").filter((word) => word.length > 0);
var firstCharacter = (text) => [...text][0] ?? "";
var Uniscript = class _Uniscript {
  index;
  #warnings = [];
  constructor(index2) {
    this.index = index2;
  }
  /**
   * The chunks of a chunked index that converting `text` both ways and rendering it as HTML still needs: a dry run in
   * lenient mode. Empty for a whole index.
   */
  missingChunks(text) {
    let converted = "";
    try {
      converted = this.convert(text, "lenient").text;
    } catch {
    }
    this.html(this.metaRuns(converted).styled);
    this.toUniscript(text);
    this.toUniscript(converted);
    return this.index.takeMissing?.() ?? [];
  }
  /** Fetches the chunks converting `text` needs, until no lookup misses; then every function gives the whole index's results */
  async ensure(text) {
    for (let missing = this.missingChunks(text); missing.length > 0; missing = this.missingChunks(text)) {
      await this.index.loadChunks?.(missing);
    }
  }
  #name(key) {
    return this.index.get(Table.names, key);
  }
  #isBlock(name) {
    return this.#name(`${name} `) !== void 0;
  }
  /** A font style of the entities: `cuneiform-hittite`, `han-japanese` */
  font(name) {
    const entry = this.index.entry(Table.fonts, `${name} `);
    if (!entry) return void 0;
    const field = (field2) => this.index.get(Table.fonts, `${name} ${field2}`) ?? "";
    return { name: entry[0].trimEnd(), lang: field("lang"), families: list(field("families")), features: list(field("features")) };
  }
  /** The CSS declaration template of a meta key (`color` → `color: {}`) */
  metaTemplate(key) {
    return this.index.get(Table.meta, key);
  }
  /** Tagged text → plain text and meta runs; unknown keys and unmatched closes warn */
  metaRuns(tagged) {
    const { styled, warnings } = Styled.parse(tagged);
    for (const run of styled.runs) {
      if (this.metaTemplate(run.key) === void 0) warnings.push({ message: `unknown meta key ${run.key}`, at: run.at });
    }
    warnings.sort((a, b) => a.at - b.at);
    return { styled, warnings };
  }
  /** HTML of tagged text: each meta run a `<span>` with its lang and CSS; an unknown key becomes a `data-` attribute */
  html(styled) {
    return styled.interleaved((run) => this.#span(run), "</span>", escapeHTML);
  }
  #span(run) {
    const attribute = (name, value) => ` ${name}="${escapeHTML(value)}"`;
    const quoted = (items) => items.map((item) => `'${item}'`).join(", ");
    let attributes = "";
    const style = [];
    const font = this.font(run.value);
    const template = this.metaTemplate(run.key);
    if (run.key === FONT_KEY && font) {
      attributes += attribute(LANG_KEY, font.lang);
      style.push(`font-family: ${quoted(font.families)}`);
      if (font.features.length) style.push(`font-feature-settings: ${quoted(font.features)}`);
    } else if (run.key === FONT_KEY && template !== void 0) {
      style.push(template.replaceAll(VALUE_PLACEHOLDER, quoted([run.value])));
    } else if (run.key === LANG_KEY) {
      attributes += attribute(LANG_KEY, run.value);
    } else if (template !== void 0) {
      style.push(template.replaceAll(VALUE_PLACEHOLDER, run.value));
    } else {
      attributes += attribute(`data-${run.key}`, run.value);
    }
    if (style.length) attributes += attribute("style", style.join("; "));
    return `<span${attributes}>`;
  }
  #warn(message, at) {
    this.#warnings.push({ message, at });
  }
  /** The control a block puts after a character of its script, or after any character; "": the effect cannot apply
   * to that script */
  #suffixOf(block, character) {
    const script = scriptOf(character);
    const scripted = script ? this.#name(`${block} ${SUFFIX_KEY} ${script}`) : void 0;
    return scripted ?? this.#name(`${block} ${SUFFIX_KEY}`);
  }
  /** The control of an effect after one character. Without one, a block with a `*meta` fallback (the colors:
   * `red *meta` → `color red`) becomes that attached meta sequence, anything else nothing; both warn. */
  #effectControl(block, character, at) {
    const suffix = this.#suffixOf(block, character);
    if (suffix) return { suffix };
    const fallback = splitOnce(this.#name(`${block} ${META_FALLBACK_KEY}`) ?? "", " ");
    if (fallback) {
      this.#warn(`${block} on ${character} kept as ${fallback[0]} meta`, at);
      return { meta: Meta.attached(...fallback).tags() };
    }
    this.#warn(`${block} does not apply to ${character}`, at);
    return {};
  }
  /** The suffix controls of the stacked effect words (`mirror` in `<:mirror red A>`) for one character, then the meta
   * sequences of the effects it has no control for: a meta follows the character's suffix controls */
  #effectSuffixes(effects, character, at) {
    const controls = effects.map((effect) => this.#effectControl(effect, character, at));
    return controls.map((control) => control.suffix ?? "").join("") + controls.map((control) => control.meta ?? "").join("");
  }
  /** One character in a block: its own entry (greek a → α), else followed by the block's suffix; then the effects.
   * A character the block has neither for stays plain, with a warning. */
  #styled(block, character, effects, at) {
    let styled = this.#name(`${block} ${character}`);
    if (styled === void 0 && this.#suffixOf(block, character) === void 0) {
      this.#warn(`no ${block} form of ${character}`, at);
      styled = character;
    }
    if (styled === void 0) return character + this.#effectSuffixes([block, ...effects], character, at);
    return styled + this.#effectSuffixes(effects, character, at);
  }
  /** A block with a suffix control (mirror, red), which stacks as an effect instead of restyling */
  #isEffect(block) {
    return this.#name(`${block} ${SUFFIX_KEY}`) !== void 0;
  }
  #form(block, operand) {
    return this.#name(`${block} ${operand}`);
  }
  /** The block and plain operand a character spells back as: 𝐚 → [bold, a], α → ["", alpha] */
  #spelling(character) {
    const form = this.index.get(Table.chars, character);
    if (!form?.startsWith("<:") || !form.endsWith(TAG_CLOSE)) return void 0;
    const content = form.slice(2, -1);
    const split = splitOnce(content, " ");
    return split && this.#isBlock(split[0]) ? split : ["", content];
  }
  /** The block that combines styles in any order: bold + sans + italic → sans-bold-italic */
  #combined(styles) {
    const parts = [...new Set(styles.flatMap((style) => style.split("-")).filter((part) => part.length > 0))].sort();
    return permutations(parts).map((order) => order.join("-")).find((name) => this.#isBlock(name));
  }
  /** A character in further styles: in the block combining them with its own style (bold on 𝛼 → bold-italic α),
   * else one style after the other, each commuting with the character's own style where they do not combine
   * (greek on 𝐚 → bold of greek a → 𝛂). A style that cannot apply keeps the character, with a warning. */
  #restyled(styles, character, at) {
    const spelling = this.#spelling(character);
    if (spelling) {
      const [own, operand] = spelling;
      const all = own ? [...styles, own] : styles;
      const base = own && characterCount(operand) > 1 ? this.#name(operand) ?? operand : operand;
      const block = this.#combined(all);
      const form = block === void 0 ? void 0 : this.#form(block, base);
      if (form !== void 0) return form;
    }
    return styles.reduceRight((text, style) => {
      const characters = [...text];
      if (characters.length !== 1) return text;
      const restyled = this.#restyledBy(style, characters[0]);
      if (restyled !== void 0) return restyled;
      this.#warn(`no ${style} form of ${characters[0]}`, at);
      return text;
    }, character);
  }
  #restyledBy(style, character) {
    const form = this.#form(style, character);
    if (form !== void 0) return form;
    const spelling = this.#spelling(character);
    if (!spelling) return void 0;
    const [own, operand] = spelling;
    if (!own) return this.#form(style, operand);
    const named = characterCount(operand) > 1 ? this.#name(operand) ?? operand : operand;
    if (characterCount(named) !== 1) return void 0;
    const restyled = this.#restyledBy(style, named);
    if (restyled === void 0) return void 0;
    return restyled === named ? character : this.#form(own, restyled);
  }
  /** One operand: its own entry (red circle → 🔴, greek eta → η), else each character or pair (greek th → θ)
   * of the operand, or of the entity it names */
  #operand(block, token, effects, at) {
    const own = this.#name(`${block} ${token}`);
    if (own !== void 0) return afterBase(own, this.#effectSuffixes(effects, firstCharacter(own) || " ", at));
    const named = this.#name(token);
    const characters = [...named !== void 0 && utf8Length(token) > 1 ? named : token];
    let out = "";
    for (let i = 0; i < characters.length; ) {
      const pair = characters.slice(i, i + 2);
      const ownPair = pair.length === 2 ? this.#name(`${block} ${pair.join("")}`) : void 0;
      if (ownPair !== void 0) {
        out += ownPair + this.#effectSuffixes(effects, characters[i], at);
        i += 2;
      } else {
        out += this.#styled(block, characters[i], effects, at);
        i += 1;
      }
    }
    return out;
  }
  /** The text inside a full block (`<:greek> filosofia kosmos<:/greek>`) as written: its whitespace stays, each word is an
   * operand; a group block joins its parts */
  #blockText(block, text, at) {
    if (this.#isGroup(block)) return this.#group(block, void 0, text, at);
    return (text.match(WHITESPACE_ENDED_PIECES) ?? []).map((piece) => {
      const word = piece.trimEnd();
      return this.#operand(block, word, [], at) + piece.slice(word.length);
    }).join("");
  }
  /** The words of an inline tag as operands of the block: a run of words that names one operand stays one (seated man,
   * red crown), the longest run first */
  #operandTokens(block, content) {
    const all = content.split(/\s+/).filter((word) => word.length > 0);
    const tokens = [];
    for (let start = 0; start < all.length; ) {
      let end = Math.min(all.length, start + MAX_OPERAND_WORDS);
      while (end > start + 1 && this.#form(block, all.slice(start, end).join("-")) === void 0) end--;
      tokens.push(all.slice(start, end).join("-"));
      start = end;
    }
    return tokens;
  }
  /** Whether the content starts with an operand of the block: `<:egyptian red crown>` names a sign, red is no effect */
  #startsOperand(block, content) {
    const first = this.#operandTokens(block, content)[0];
    return first !== void 0 && this.#form(block, first) !== void 0;
  }
  /** The space separated operands of an inline tag, spaces dropped */
  #operands(block, content, effects, at) {
    return this.#operandTokens(block, content).map((token) => this.#operand(block, token, effects, at)).join("");
  }
  #isGroup(block) {
    return this.#form(block, GROUP_KEY) !== void 0;
  }
  /** A group (above, beside) joins its parts unstyled with the prefix before or the infix between them that the script of
   * the first part has; the parts are operands of the naming block (`<:egyptian above A1 A2>`), else names or text */
  #group(group, naming, content, at) {
    const tokens = naming === void 0 ? words(content.replace(/\s+/g, " ")) : this.#operandTokens(naming, content);
    const innerAt = tokens.findIndex((token, position) => position > 0 && this.#isGroup(token));
    const inner = innerAt > 0 ? tokens.splice(innerAt) : [];
    const parts = tokens.map((token) => (naming === void 0 ? void 0 : this.#form(naming, token)) ?? (utf8Length(token) > 1 ? this.#name(token) : void 0) ?? token);
    if (!parts.length) return "";
    const script = scriptOf(firstCharacter(parts[0]));
    const affix = (kind) => this.#name(`${group} ${kind} ${script}`);
    const [prefix, infix] = [affix("*prefix"), affix("*infix")];
    if (prefix === void 0 && infix === void 0) this.#warn(`no ${group} group of ${parts[0]}`, at);
    if (inner.length) {
      parts.push((affix("*open") ?? "") + this.#group(inner[0], naming, inner.slice(1).join(" "), at) + (affix("*close") ?? ""));
    }
    return (prefix ?? "") + parts.join(infix ?? "");
  }
  /** The text of `<:content>` at byte `at` that is no block opener or closer */
  #tag(content, at) {
    if (utf8Length(content) === 1) return content;
    const text = this.#name(content.replaceAll(" ", "-"));
    if (text !== void 0) return text;
    const codePoint = this.#codePoint(content, `<:${content}>`, at);
    if (codePoint !== void 0) return codePoint;
    const meta = this.#metaTag(content, at);
    if (meta !== void 0) return meta;
    const split = content.includes(" ") ? content.indexOf(" ") : content.indexOf("-");
    const [first, rest] = [content.slice(0, split), content.slice(split + 1)];
    if (split >= 0 && this.#isBlock(first)) {
      const blocks = [first];
      let operands = rest;
      for (let next = splitOnce(operands, " "); next && this.#isBlock(next[0]); next = splitOnce(operands, " ")) {
        if (this.#startsOperand(blocks[blocks.length - 1], operands)) break;
        blocks.push(next[0]);
        operands = next[1];
      }
      const groupAt = blocks.findIndex((word) => this.#isGroup(word));
      if (groupAt >= 0) {
        const [group] = blocks.splice(groupAt, 1);
        return this.#group(group, blocks.findLast((word) => !this.#isEffect(word)), operands, at);
      }
      const block = blocks.pop();
      const effects = blocks.filter((word) => this.#isEffect(word));
      const styles = blocks.filter((word) => !this.#isEffect(word));
      if (!styles.length) return this.#operands(block, operands, effects, at);
      return [...this.#operands(block, operands, [], at)].map((character) => this.#restyled(styles, character, at) + this.#effectSuffixes(effects, character, at)).join("");
    }
    const lowercased = this.#name(content.replace(/[A-Z]/g, (capital) => capital.toLowerCase()).replaceAll(" ", "-"));
    if (lowercased !== void 0) return lowercased;
    throw new UniscriptError("UnknownEntity", content);
  }
  /** `<:key value …>` with meta keys: `<:font han-japanese>` opens spans, `<:color #ff8800 mirror A>` attaches to each
   * character of the rest; undefined when the content starts with no meta key and value */
  #metaTag(content, at) {
    const sequences = [];
    let rest = content.trimStart();
    for (let next = splitOnce(rest, " "); next && this.metaTemplate(next[0]) !== void 0; next = splitOnce(rest, " ")) {
      const key = next[0];
      const after = next[1].trimStart();
      const [value, remaining] = splitOnce(after, " ") ?? [after, ""];
      if (!isMetaValue(value)) throw new UniscriptError("InvalidMeta", content);
      if (key === FONT_KEY && !this.font(value)) this.#warn(`${value} is no font style of the entities, used as a font family`, at);
      sequences.push([key, value]);
      rest = remaining.trimStart();
    }
    if (!sequences.length) return void 0;
    if (!rest) return sequences.map(([key, value]) => Meta.open(key, value).tags()).join("");
    const attached = sequences.map(([key, value]) => Meta.attached(key, value).tags()).join("");
    return attach(this.#metaOperands(rest, at), attached);
  }
  /** The characters a meta attaches to: a tag content (`mirror A`, `alpha`), else space separated names and texts */
  #metaOperands(rest, at) {
    try {
      return this.#tag(rest, at);
    } catch (error) {
      if (!(error instanceof UniscriptError)) throw error;
    }
    const isName = (token) => token.length > 1 && [...token].every(isNameCharacter);
    return words(rest).map((token) => isName(token) ? this.#tag(token, at) : token).join("");
  }
  /** Uniscript → Unicode (meta information as TAG sequences) and the warnings; in mode "error" the first warning
   * is the error */
  convert(source, mode = "warn") {
    this.#warnings = [];
    const text = this.#unicodeOf(source, mode);
    const warnings = this.#warnings;
    this.#warnings = [];
    if (mode === "error" && warnings.length) throw new UniscriptError("Unsupported", warnings[0]);
    return { text, warnings };
  }
  /** The character of a code point token (`U+1F60D`, `1F60D`); an invalid one (surrogate, above 10FFFF) warns and stays
   * `written`; undefined for no code point token */
  #codePoint(token, written, at) {
    const value = codePointValue(token);
    if (value === void 0) return void 0;
    if (value <= MAX_CODE_POINT && (value < SURROGATES[0] || value > SURROGATES[1])) return String.fromCodePoint(value);
    this.#warn(`invalid code point U+${value.toString(16).toUpperCase().padStart(4, "0")}`, at);
    return written;
  }
  /** The source text of an error, with a warning, in mode "lenient"; else the error */
  #kept(error, source, at, mode) {
    if (mode !== "lenient") throw error;
    this.#warn(error.message, at);
    return source;
  }
  /** The next `<:`, `\:` or `\U1F60D` from `position`, else the end */
  static #marker(source, position) {
    MARKERS.lastIndex = position;
    return MARKERS.exec(source)?.index ?? source.length;
  }
  #unicodeOf(source, mode) {
    let out = "";
    let block;
    let position = this.#headerEnd(source);
    let bytes = utf8Length(source.slice(0, position));
    const advance = (to) => {
      bytes += utf8Length(source.slice(position, to));
      position = to;
    };
    while (position < source.length) {
      const marker = _Uniscript.#marker(source, position);
      const plain = source.slice(position, marker);
      out += block !== void 0 ? this.#blockText(block, plain, bytes) : plain;
      advance(marker);
      if (position >= source.length) break;
      const escaped = unicodeEscapeAt(source, position + 1);
      if (escaped !== void 0) {
        const end = position + 2 + escaped.length;
        out += this.#codePoint(escaped, source.slice(position, end), bytes);
        advance(end);
        continue;
      }
      if (source.startsWith(SHORT_OPEN, position)) {
        const nameEnd = position + 2 + matchAt(NAME_TOKEN, source, position + 2)[0].length;
        const name = source.slice(position + 2, nameEnd);
        const written = source.slice(position, nameEnd);
        out += this.#name(name) ?? this.#codePoint(name, written, bytes) ?? this.#kept(new UniscriptError("UnknownEntity", name), written, bytes, mode);
        advance(nameEnd);
        continue;
      }
      const close = source.indexOf(TAG_CLOSE, position + 2);
      if (close < 0) {
        const rest = source.slice(position);
        out += this.#kept(new UniscriptError("Unclosed", rest), rest, bytes, mode);
        break;
      }
      const content = source.slice(position + 2, close);
      const closedKey = content.startsWith(CLOSING_SLASH) ? content.slice(1) : void 0;
      if (closedKey !== void 0 && this.metaTemplate(closedKey) !== void 0) {
        out += Meta.close(closedKey).tags();
      } else if (isClosing(content)) {
        block = void 0;
      } else if (this.#isBlock(content)) {
        block = content;
      } else {
        try {
          out += this.#tag(content, bytes);
        } catch (error) {
          if (!(error instanceof UniscriptError)) throw error;
          out += this.#kept(error, source.slice(position, close + 1), bytes, mode);
        }
      }
      advance(close + 1);
    }
    return out;
  }
  /** UTF-16 length of the header to skip; a version that is no uniscript.org version ({@link readsVersion}) warns */
  #headerEnd(source) {
    const found = headerOf(source);
    if (!found) return 0;
    if (!readsVersion(found.version)) this.#warn(`unsupported uniscript version ${found.version}`, 0);
    return found.end;
  }
  /** One character and the block types of the suffix controls after it: `<:mirror red A>`, `<:mirror red circle>` */
  #spelled(character, blocks) {
    const own = this.index.get(Table.chars, character);
    if (!blocks.length) return own ?? character;
    const inner = own !== void 0 ? own.slice(2, -1) : character;
    return `<:${blocks.join(" ")} ${inner}>`;
  }
  #knownMeta(text, position) {
    const found = metaAt(text, position);
    return found && this.metaTemplate(found.meta.key) !== void 0 ? found : void 0;
  }
  /** The spelling of the longest known emoji sequence joined at `position`: 👩‍🦰 → <:red-haired woman> */
  #joinedForm(text, position) {
    for (const length of joinedPrefixes(text, position)) {
      const form = this.index.get(Table.chars, text.slice(position, position + length));
      if (form !== void 0) return { form, length };
    }
    return void 0;
  }
  /** Unicode → uniscript; meta sequences of known keys become `<:font han-japanese>`, `<:/font>`, `<:color red A>` */
  toUniscript(text) {
    let out = "";
    let position = 0;
    while (position < text.length) {
      const span = this.#knownMeta(text, position);
      if (span && span.meta.kind !== "attached") {
        out += span.meta.uniscript();
        position += span.length;
        continue;
      }
      const joined = this.#joinedForm(text, position);
      if (joined) {
        out += joined.form;
        position += joined.length;
        continue;
      }
      const character = String.fromCodePoint(text.codePointAt(position));
      position += character.length;
      if ((character === TAG_OPEN || character === SHORT_OPEN) && text.startsWith(MARKER_COLON, position)) {
        position += 1;
        out += character + ESCAPED_COLON;
        continue;
      }
      if (character === SHORT_OPEN && unicodeEscapeAt(text, position) !== void 0) {
        position += 1;
        out += character + ESCAPED_UNICODE;
        continue;
      }
      const emojiTags = emojiTagsAt(text, position);
      if (emojiTags !== void 0) {
        out += this.#spelled(character, []) + text.slice(position, position + emojiTags);
        position += emojiTags;
        continue;
      }
      const suffixes = [];
      while (position < text.length) {
        const next = String.fromCodePoint(text.codePointAt(position));
        const block = this.index.get(Table.suffixes, next);
        if (block === void 0) break;
        suffixes.push(block);
        position += next.length;
      }
      if (suffixes.length) suffixes.push(suffixes.shift());
      const attached = [];
      for (let meta = this.#knownMeta(text, position); meta?.meta.kind === "attached"; meta = this.#knownMeta(text, position)) {
        attached.push(meta.meta.uniscript());
        position += meta.length;
      }
      const spelled = this.#spelled(character, suffixes);
      if (!attached.length) {
        out += spelled;
        continue;
      }
      const form = spelled.startsWith("<:") && spelled.endsWith(TAG_CLOSE) ? spelled.slice(2, -1) : spelled;
      out += `<:${attached.join(" ")} ${form}>`;
    }
    return out;
  }
};

// src/completion.ts
var MAX_SUGGESTIONS = 1e3;
var GROUP_SAMPLES = 3;
var BLOCK_DETAIL = "block";
var SEGMENT_END = "-";
var TAG_END = ">";
var TYPED_TAG = /(?:<:(?! )([^<>\n[\]{};="]*)|\\:([A-Za-z0-9_-]*))$/;
function namesOf(index2) {
  const names2 = { entities: [], blocks: /* @__PURE__ */ new Set(), operands: /* @__PURE__ */ new Map() };
  for (const [key, text] of index2.entries(Table.names)) {
    const space = key.indexOf(" ");
    if (space < 0) names2.entities.push([key, text]);
    else if (space === key.length - 1) names2.blocks.add(key.trimEnd());
    else if (key[space + 1] !== "*") {
      const block = key.slice(0, space);
      if (!names2.operands.has(block)) names2.operands.set(block, []);
      names2.operands.get(block).push([key.slice(space + 1), text]);
    }
  }
  return names2;
}
var shortestFirst = (a, b) => a[0].length - b[0].length || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
var startsWith = (name, prefix) => name.toLowerCase().startsWith(prefix.toLowerCase());
function summary(members) {
  return `${[...members].sort(shortestFirst).slice(0, GROUP_SAMPLES).map(([, text]) => text).join("")}\u2026 ${members.length}`;
}
function grouped(candidates, prefix) {
  const matching = candidates.filter(([name]) => startsWith(name, prefix));
  let start = prefix.length;
  for (; ; ) {
    const groups = /* @__PURE__ */ new Map();
    for (const named of matching) {
      const end = named[0].indexOf(SEGMENT_END, start);
      const key = end < 0 ? named[0] : named[0].slice(0, end + 1);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(named);
    }
    if (groups.size === 1 && matching.length > 1) {
      start = [...groups.keys()][0].length;
      continue;
    }
    return [...groups].map(([key, members]) => members.length === 1 ? { name: members[0][0], detail: members[0][1], size: 1 } : { name: key, detail: summary(members), size: members.length }).sort((a, b) => shortestFirst([a.name, ""], [b.name, ""])).slice(0, MAX_SUGGESTIONS);
  }
}
function suggestions(lineBeforeCursor, nextCharacter, names2) {
  const match = TYPED_TAG.exec(lineBeforeCursor);
  if (!match) return void 0;
  const isShort = match[2] !== void 0;
  const marker = isShort ? "\\:" : "<:";
  const words2 = (isShort ? match[2] : match[1]).split(" ");
  let leading = 0;
  while (leading < words2.length - 1 && names2.blocks.has(words2[leading])) leading++;
  const head = marker + words2.slice(0, leading).map((word) => word + " ").join("");
  const prefix = words2.slice(leading).join(SEGMENT_END);
  const candidates = leading ? names2.operands.get(words2[leading - 1]) ?? [] : names2.entities;
  const closes = !leading && !isShort && nextCharacter !== TAG_END;
  const items = grouped(candidates, prefix).map(({ name, detail, size }) => size > 1 ? { name, detail, kind: "group", written: head + name } : { name, detail, kind: "name", written: head + name + (closes ? TAG_END : "") });
  if (!isShort && !leading) {
    for (const block of [...names2.blocks].sort()) {
      if (!startsWith(block, prefix)) continue;
      const operands = names2.operands.get(block);
      items.push({ name: block, detail: operands ? summary(operands) : BLOCK_DETAIL, kind: "block", written: `${head}${block} ` });
    }
  }
  return { tagStart: match.index, isShort, items: items.slice(0, MAX_SUGGESTIONS) };
}

// src/tags.ts
var TAG = /<:(?:[^\s>][^>\n[\]{};="]*)?>|\\:(?:[Uu]\+)?[A-Za-z0-9_-]+|\\U[0-9A-Fa-f]{4,8}(?![A-Za-z0-9_-])/g;
function tagAt(line, column) {
  for (const match of line.matchAll(TAG)) {
    const end = match.index + match[0].length;
    if (match.index <= column && column <= end) return { start: match.index, end, text: match[0] };
  }
  return void 0;
}

// src/extension.ts
var INDEX_FILE = "entities.idx";
var ALL_DOCUMENTS = { pattern: "**" };
var TRIGGER_CHARACTERS = [":", " ", "-"];
var SETTINGS = "uniscript";
var INSERTS_SETTING = "completionInserts";
var TAG_END2 = ">";
var REOPEN_SUGGESTIONS = { command: "editor.action.triggerSuggest", title: "" };
var ITEM_KINDS = {
  name: vscode.CompletionItemKind.Constant,
  group: vscode.CompletionItemKind.Folder,
  block: vscode.CompletionItemKind.Keyword
};
var converter;
var index;
var loadedNames;
var names = () => loadedNames ??= namesOf(index);
function unicodeOf(tag) {
  try {
    return converter.convert(tag, "lenient").text || void 0;
  } catch {
    return void 0;
  }
}
function completionItem(suggestion, order, typed, replaced, closedRange, isShort) {
  const item = new vscode.CompletionItem({ label: suggestion.name, description: suggestion.detail }, ITEM_KINDS[suggestion.kind]);
  item.filterText = typed + suggestion.written.slice(typed.length);
  item.sortText = String(order).padStart(5, "0");
  item.insertText = suggestion.written;
  item.range = replaced;
  if (suggestion.kind !== "name") {
    item.command = REOPEN_SUGGESTIONS;
  } else if (vscode.workspace.getConfiguration(SETTINGS).get(INSERTS_SETTING) === "character") {
    const tag = suggestion.written.endsWith(TAG_END2) || isShort ? suggestion.written : suggestion.written + TAG_END2;
    const unicode = unicodeOf(tag);
    if (unicode) {
      item.insertText = unicode;
      item.range = closedRange;
      item.detail = tag;
    }
  }
  return item;
}
var completionProvider = {
  provideCompletionItems(document, position) {
    const line = document.lineAt(position).text;
    const next = line.charAt(position.character);
    const found = suggestions(line.slice(0, position.character), next, names());
    if (!found?.items.length) return void 0;
    const start = position.with({ character: found.tagStart });
    const closedEnd = next === TAG_END2 && !found.isShort ? position.translate(0, 1) : position;
    const typed = line.slice(found.tagStart, position.character);
    const items = found.items.map((suggestion, order) => completionItem(suggestion, order, typed, new vscode.Range(start, position), new vscode.Range(start, closedEnd), found.isShort));
    return new vscode.CompletionList(items, true);
  }
};
function tagUnderCursor(document, position) {
  const tag = tagAt(document.lineAt(position).text, position.character);
  const unicode = tag && unicodeOf(tag.text);
  return tag && unicode ? { range: new vscode.Range(position.line, tag.start, position.line, tag.end), unicode } : void 0;
}
var hoverProvider = {
  provideHover(document, position) {
    const tag = tagUnderCursor(document, position);
    if (!tag) return void 0;
    const codePoints = [...tag.unicode].map((character) => "U+" + character.codePointAt(0).toString(16).toUpperCase().padStart(4, "0"));
    return new vscode.Hover(new vscode.MarkdownString(`**${tag.unicode}**  ${codePoints.join(" ")}`), tag.range);
  }
};
var codeActionProvider = {
  provideCodeActions(document, range) {
    const tag = tagUnderCursor(document, range.start);
    if (!tag) return void 0;
    const action = new vscode.CodeAction(`Replace with ${tag.unicode}`, vscode.CodeActionKind.QuickFix);
    action.edit = new vscode.WorkspaceEdit();
    action.edit.replace(document.uri, tag.range, tag.unicode);
    return [action];
  }
};
async function convertEditor(convert) {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const { document } = editor;
  const selected = editor.selections.filter((selection) => !selection.isEmpty);
  const ranges = selected.length ? selected : [new vscode.Range(document.positionAt(0), document.positionAt(document.getText().length))];
  await editor.edit((edit) => ranges.forEach((range) => edit.replace(range, convert(document.getText(range)))));
}
function toUnicode(text) {
  const { text: converted, warnings } = converter.convert(text, "lenient");
  if (warnings.length) vscode.window.setStatusBarMessage(`uniscript: ${warnings.map((warning) => warning.message).join("; ")}`, 1e4);
  return converted;
}
function activate(context) {
  index = new EntityIndex((0, import_node_fs.readFileSync)(context.asAbsolutePath(INDEX_FILE)));
  converter = new Uniscript(index);
  context.subscriptions.push(
    vscode.languages.registerCompletionItemProvider(ALL_DOCUMENTS, completionProvider, ...TRIGGER_CHARACTERS),
    vscode.languages.registerHoverProvider(ALL_DOCUMENTS, hoverProvider),
    vscode.languages.registerCodeActionsProvider(ALL_DOCUMENTS, codeActionProvider, { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }),
    vscode.commands.registerCommand("uniscript.toUnicode", () => convertEditor(toUnicode)),
    vscode.commands.registerCommand("uniscript.toUniscript", () => convertEditor((text) => converter.toUniscript(text)))
  );
}
function deactivate() {
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  activate,
  deactivate
});
