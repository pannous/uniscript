package com.pannous.uniscript.ffi;

/** A conversion that failed: in {@link Uniscript.Mode#WARN} an unknown entity, an unclosed {@code <:} or an invalid
 * meta value; in {@link Uniscript.Mode#ERROR} also the first unsupported character */
public final class UniscriptException extends RuntimeException {
	/** The kinds of c/uniscript.h's uniscript_error_kind, in its order */
	public enum Kind { UNKNOWN_ENTITY, UNCLOSED, UNSUPPORTED, INVALID_META, INVALID_INPUT }

	private final Kind kind;
	private final String detail;
	private final Uniscript.Warning warning;

	UniscriptException(Kind kind, String message, String detail, Uniscript.Warning warning) {
		super(message);
		this.kind = kind;
		this.detail = detail;
		this.warning = warning;
	}

	public Kind kind() {
		return kind;
	}

	/** The unknown name, the rest of the text from an unclosed {@code <:}, the warning message or the meta tag content */
	public String detail() {
		return detail;
	}

	/** The unsupported character's warning for {@link Kind#UNSUPPORTED}, else null */
	public Uniscript.Warning warning() {
		return warning;
	}
}
