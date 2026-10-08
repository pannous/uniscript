package com.pannous.uniscript.ffi;

import java.lang.foreign.Arena;
import java.lang.foreign.MemorySegment;
import java.lang.foreign.SegmentAllocator;
import java.lang.foreign.StructLayout;
import java.lang.invoke.MethodHandle;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

import static com.pannous.uniscript.ffi.NativeLibrary.FONT;
import static com.pannous.uniscript.ffi.NativeLibrary.META_RUN;
import static com.pannous.uniscript.ffi.NativeLibrary.RESULT;
import static com.pannous.uniscript.ffi.NativeLibrary.STYLED;
import static com.pannous.uniscript.ffi.NativeLibrary.WARNING;
import static com.pannous.uniscript.ffi.NativeLibrary.array;
import static com.pannous.uniscript.ffi.NativeLibrary.pointer;
import static com.pannous.uniscript.ffi.NativeLibrary.size;
import static com.pannous.uniscript.ffi.NativeLibrary.string;
import static java.lang.foreign.ValueLayout.ADDRESS;
import static java.lang.foreign.ValueLayout.JAVA_INT;
import static java.lang.foreign.ValueLayout.JAVA_LONG;

/**
 * ASCII names for Unicode text and back: {@code Uniscript.toUnicode("\\:alpha \\:fracture-A")} is "α 𝔄",
 * {@code Uniscript.toUniscript("α 𝔄")} is "\\:alpha \\:fracture-A". Backed by the Rust core through the
 * C ABI of c/uniscript.h. All offsets (at, start, end, length) are UTF-8 byte offsets. Thread-safe.
 */
public final class Uniscript {
	/** The current uniscript version of the header {@code <:uniscript version="…">}; every https://uniscript.org/vN
	 * is read without warning, a foreign version URL warns */
	public static final String VERSION = "https://uniscript.org/v1";
	private static final System.Logger LOGGER = System.getLogger("com.pannous.uniscript.ffi");

	/** WARN: unsupported characters stay plain with a warning; ERROR: the first warning is the error; LENIENT: errors
	 * too become warnings and their uniscript stays as written. In the order of c/uniscript.h's uniscript_mode. */
	public enum Mode { WARN, ERROR, LENIENT }

	/** A character or combination without a Unicode counterpart, at a byte offset of the source */
	public record Warning(String message, long at) {
		@Override
		public String toString() {
			return "uniscript: " + message + " at byte " + at;
		}
	}

	/** Converted text and its warnings */
	public record Result(String text, List<Warning> warnings) {}

	/** The header {@code <:uniscript version="…">}: its version ("" when it names none), its length in bytes with the
	 * line break after it */
	public record Header(String version, long length) {}

	/** A byte range of the plain text under one meta key; at: offset of its sequence in the tagged text */
	public record MetaRun(String key, String value, long start, long end, long at) {}

	/** Plain text without its meta sequences, the runs they cover (nested, in opening order) and the warnings */
	public record Styled(String text, List<MetaRun> runs, List<Warning> warnings) {}

	/** A font style of the entities: the value of {@code <:font cuneiform-hittite>}; lang is BCP 47 */
	public record Font(String name, String lang, List<String> families, List<String> features) {}

	private Uniscript() {}

	/** Uniscript → Unicode, leniently: faulty uniscript stays as written; warnings go to the logger com.pannous.uniscript.ffi */
	public static String toUnicode(String source) {
		Result result = convert(source);
		result.warnings().forEach(warning -> LOGGER.log(System.Logger.Level.WARNING, warning.toString()));
		return result.text();
	}

	/** Unicode → uniscript; {@link #toUnicode} gives the text back */
	public static String toUniscript(String text) {
		return takeString(call(NativeLibrary.TO_UNISCRIPT, text));
	}

	/** Unicode → uniscript in ASCII only: a character without a name is written by its code point ({@code \:U+E000}) */
	public static String toAsciiUniscript(String text) {
		return takeString(call(NativeLibrary.TO_ASCII_UNISCRIPT, text));
	}

	/** The source with its opener-like inline tags in explicit form ({@code <:alpha>} → {@code \:alpha}), which converts alike */
	public static String explicit(String source) {
		return takeString(call(NativeLibrary.EXPLICIT, source));
	}

	/** Uniscript → Unicode (meta information as TAG sequences) and the warnings, leniently */
	public static Result convert(String source) {
		return convert(source, Mode.LENIENT);
	}

	/** Uniscript → Unicode (meta information as TAG sequences) and the warnings
	 * @throws UniscriptException on an error of the mode */
	public static Result convert(String source, Mode mode) {
		Objects.requireNonNull(mode, "mode");
		try (Arena arena = Arena.ofConfined()) {
			return takeResult((MemorySegment) NativeLibrary.CONVERT.invokeExact(
					(SegmentAllocator) arena, arena.allocateFrom(Objects.requireNonNull(source, "source")), mode.ordinal()));
		} catch (Throwable failure) {
			throw rethrown(failure);
		}
	}

	/** HTML of tagged text: each meta run a {@code <span>} with its lang and CSS; the warnings of {@link #metaRuns} */
	public static Result html(String tagged) {
		try (Arena arena = Arena.ofConfined()) {
			return takeResult((MemorySegment) NativeLibrary.HTML.invokeExact(
					(SegmentAllocator) arena, arena.allocateFrom(Objects.requireNonNull(tagged, "tagged"))));
		} catch (Throwable failure) {
			throw rethrown(failure);
		}
	}

	/** Tagged text → plain text and meta runs; unknown keys and unmatched closes warn */
	public static Styled metaRuns(String tagged) {
		try (Arena arena = Arena.ofConfined()) {
			MemorySegment styled = (MemorySegment) NativeLibrary.META_RUNS.invokeExact(
					(SegmentAllocator) arena, arena.allocateFrom(Objects.requireNonNull(tagged, "tagged")));
			try {
				List<MetaRun> runs = array(pointer(styled, STYLED, "runs"), size(styled, STYLED, "run_count"), META_RUN,
						run -> new MetaRun(string(run, META_RUN, "key"), string(run, META_RUN, "value"),
								size(run, META_RUN, "start"), size(run, META_RUN, "end"), size(run, META_RUN, "at")));
				return new Styled(string(styled, STYLED, "text"), runs, warnings(styled, STYLED));
			} finally {
				NativeLibrary.STYLED_FREE.invokeExact(styled);
			}
		} catch (Throwable failure) {
			throw rethrown(failure);
		}
	}

	/** The header {@code <:uniscript …>} the source starts with */
	public static Optional<Header> header(String source) {
		try (Arena arena = Arena.ofConfined()) {
			byte[] bytes = Objects.requireNonNull(source, "source").getBytes(StandardCharsets.UTF_8);
			MemorySegment text = arena.allocateFrom(source);
			MemorySegment version = arena.allocate(ADDRESS), versionLength = arena.allocate(JAVA_LONG),
					length = arena.allocate(JAVA_LONG);
			if ((int) NativeLibrary.HEADER.invokeExact(text, version, versionLength, length) == 0) return Optional.empty();
			long versionBytes = versionLength.get(JAVA_LONG, 0);
			int versionStart = versionBytes == 0 ? 0 : (int) (version.get(ADDRESS, 0).address() - text.address());
			String versionText = new String(bytes, versionStart, (int) versionBytes, StandardCharsets.UTF_8);
			return Optional.of(new Header(versionText, length.get(JAVA_LONG, 0)));
		} catch (Throwable failure) {
			throw rethrown(failure);
		}
	}

	/** The font style of the entities with that name ({@code cuneiform-hittite}, {@code han-japanese}) */
	public static Optional<Font> font(String name) {
		try (Arena arena = Arena.ofConfined()) {
			MemorySegment font = arena.allocate(FONT);
			if ((int) NativeLibrary.FONT_LOOKUP.invokeExact(arena.allocateFrom(Objects.requireNonNull(name, "name")), font) == 0) {
				return Optional.empty();
			}
			try {
				return Optional.of(new Font(string(font, FONT, "name"), string(font, FONT, "lang"),
						strings(font, "families", "family_count"), strings(font, "features", "feature_count")));
			} finally {
				NativeLibrary.FONT_FREE.invokeExact(font);
			}
		} catch (Throwable failure) {
			throw rethrown(failure);
		}
	}

	/** The CSS declaration template of a meta key: "color" → "color: {}" */
	public static Optional<String> metaTemplate(String key) {
		return Optional.ofNullable(takeString(call(NativeLibrary.META_TEMPLATE, key)));
	}

	/** A function of one string returning a string the caller frees */
	private static MemorySegment call(MethodHandle function, String argument) {
		try (Arena arena = Arena.ofConfined()) {
			return (MemorySegment) function.invokeExact(arena.allocateFrom(Objects.requireNonNull(argument)));
		} catch (Throwable failure) {
			throw rethrown(failure);
		}
	}

	private static String takeString(MemorySegment text) {
		try {
			return string(text);
		} finally {
			free(NativeLibrary.FREE, text);
		}
	}

	/** The result's text and warnings, or its error thrown; frees it either way */
	private static Result takeResult(MemorySegment result) {
		try {
			int kind = result.get(JAVA_INT, NativeLibrary.offset(RESULT, "error_kind"));
			if (kind != 0) {
				UniscriptException.Kind errorKind = UniscriptException.Kind.values()[kind - 1];
				String detail = string(result, RESULT, "error_detail");
				Warning warning = errorKind == UniscriptException.Kind.UNSUPPORTED
						? new Warning(detail, size(result, RESULT, "error_at")) : null;
				throw new UniscriptException(errorKind, string(result, RESULT, "error"), detail, warning);
			}
			return new Result(string(result, RESULT, "text"), warnings(result, RESULT));
		} finally {
			free(NativeLibrary.RESULT_FREE, result);
		}
	}

	private static List<Warning> warnings(MemorySegment struct, StructLayout layout) {
		return array(pointer(struct, layout, "warnings"), size(struct, layout, "warning_count"), WARNING,
				warning -> new Warning(string(warning, WARNING, "message"), size(warning, WARNING, "at")));
	}

	private static List<String> strings(MemorySegment font, String field, String countField) {
		return array(pointer(font, FONT, field), size(font, FONT, countField), ADDRESS, item -> string(item.get(ADDRESS, 0)));
	}

	private static void free(MethodHandle free, MemorySegment pointer) {
		try {
			free.invokeExact(pointer);
		} catch (Throwable failure) {
			throw rethrown(failure);
		}
	}

	private static RuntimeException rethrown(Throwable failure) {
		if (failure instanceof RuntimeException runtime) return runtime;
		if (failure instanceof Error error) throw error;
		return new IllegalStateException(failure);
	}
}
