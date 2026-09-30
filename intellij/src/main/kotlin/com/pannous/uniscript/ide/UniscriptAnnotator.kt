// Syntax highlighting of uniscript tags in every file type, with their Unicode as tooltip and their errors and warnings
package com.pannous.uniscript.ide

import com.intellij.lang.annotation.AnnotationHolder
import com.intellij.lang.annotation.Annotator
import com.intellij.lang.annotation.HighlightSeverity
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.pannous.uniscript.codePointValue

private fun key(name: String, fallback: TextAttributesKey) = TextAttributesKey.createTextAttributesKey("UNISCRIPT_$name", fallback)

val MARKER = key("MARKER", DefaultLanguageHighlighterColors.KEYWORD)
val ENTITY = key("ENTITY", DefaultLanguageHighlighterColors.CONSTANT)
val BLOCK = key("BLOCK", DefaultLanguageHighlighterColors.METADATA)
val META_VALUE = key("META_VALUE", DefaultLanguageHighlighterColors.NUMBER)
val OPERAND = key("OPERAND", DefaultLanguageHighlighterColors.STRING)

class UniscriptAnnotator : Annotator, DumbAware {
	override fun annotate(element: PsiElement, holder: AnnotationHolder) {
		if (element !is PsiFile || !isScannedFile(element)) return
		uniscriptTags(element.viewProvider.contents).forEach { annotate(it, holder) }
	}

	private fun annotate(tag: UniscriptTag, holder: AnnotationHolder) {
		highlight(tag, holder)
		tag.convert().onSuccess { converted ->
			if (converted.text.isNotEmpty()) {
				holder.newAnnotation(HighlightSeverity.INFORMATION, converted.text).range(tag.range).create()
			}
			converted.warnings.forEach { holder.newAnnotation(HighlightSeverity.WEAK_WARNING, it.message).range(tag.range).create() }
		}.onFailure { holder.newAnnotation(HighlightSeverity.ERROR, it.message ?: "invalid uniscript").range(tag.range).create() }
	}

	/** The markers, then an entity name as a whole, else the leading block words and meta keys with their values */
	private fun highlight(tag: UniscriptTag, holder: AnnotationHolder) {
		val content = tag.contentRange
		fun paint(range: TextRange, key: TextAttributesKey) {
			if (!range.isEmpty) holder.newSilentAnnotation(HighlightSeverity.INFORMATION).range(range).textAttributes(key).create()
		}
		paint(TextRange(tag.range.startOffset, content.startOffset), MARKER)
		paint(TextRange(content.endOffset, tag.range.endOffset), MARKER)
		val text = tag.content
		if (uniscript.isName(text.replace(' ', '-')) || tag.isShort || codePointValue(text) != null) return paint(content, ENTITY)
		var offset = content.startOffset
		var operandsStart = offset
		var metaValueNext = false
		for (word in text.split(' ')) {
			val range = TextRange.from(offset, word.length)
			offset += word.length + 1
			val key = when {
				word.isEmpty() -> continue
				metaValueNext -> META_VALUE
				uniscript.isMetaKey(word.removePrefix("/")) -> BLOCK.also { metaValueNext = !word.startsWith("/") }
				uniscript.isBlock(word.removePrefix("/")) -> BLOCK
				else -> break
			}
			if (key == META_VALUE) metaValueNext = false
			paint(range, key)
			operandsStart = offset
		}
		paint(TextRange(minOf(operandsStart, content.endOffset), content.endOffset), OPERAND)
	}
}
