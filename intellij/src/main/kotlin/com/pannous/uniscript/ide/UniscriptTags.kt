// Finding uniscript tags in any file and converting them one at a time
package com.pannous.uniscript.ide

import com.intellij.lang.injection.InjectedLanguageManager
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiFile
import com.pannous.uniscript.Converted
import com.pannous.uniscript.Uniscript
import com.pannous.uniscript.UniscriptError

/** `<:content>` on one line, and `\:name`. The content starts with no space and has no brackets, braces, `;`, `=` or
 *  quotes, so Scala's `T <: Bound[…]>` and C++'s `<:` digraph are no tags. */
private val TAG = Regex("""<:(?:[^\s>][^>\n\[\]{};="]*)?>|\\:[A-Za-z0-9_-]+""")
private const val SHORT_MARKER_LENGTH = 2
private const val LONG_OPEN_LENGTH = 2

val uniscript by lazy { Uniscript() }

data class UniscriptTag(val range: TextRange, val text: String) {
	val isShort get() = text.startsWith("\\")

	/** The range between `<:` and `>`, or after `\:` */
	val contentRange: TextRange
		get() = if (isShort) TextRange(range.startOffset + SHORT_MARKER_LENGTH, range.endOffset)
		else TextRange(range.startOffset + LONG_OPEN_LENGTH, range.endOffset - 1)

	val content get() = contentRange.shiftLeft(range.startOffset).substring(text)

	/** The tag on its own in Unicode; "" for block openers and closers (`<:greek>`, `<:/greek>`) */
	fun convert(): Result<Converted> = try {
		Result.success(uniscript.convert(text))
	} catch (error: UniscriptError) {
		Result.failure(error)
	}
}

fun uniscriptTags(text: CharSequence): Sequence<UniscriptTag> =
	TAG.findAll(text).map { UniscriptTag(TextRange(it.range.first, it.range.last + 1), it.value) }

/** The main file of a view provider, once: not injected fragments nor the other language roots of the same text */
fun isScannedFile(file: PsiFile): Boolean {
	val viewProvider = file.viewProvider
	return viewProvider.getPsi(viewProvider.baseLanguage) == file &&
		!InjectedLanguageManager.getInstance(file.project).isInjectedFragment(file)
}
