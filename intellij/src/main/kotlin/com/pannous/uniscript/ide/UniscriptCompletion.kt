// Completion inside uniscript tags in every file type: entity names after `<:` and `\:`, block words, and after a
// block word its operands (`<:egyptian seated-m` → seated-man); the popup opens by itself after `<:` and `\:`
package com.pannous.uniscript.ide

import com.intellij.codeInsight.AutoPopupController
import com.intellij.codeInsight.completion.CompletionContributor
import com.intellij.codeInsight.completion.CompletionParameters
import com.intellij.codeInsight.completion.CompletionResultSet
import com.intellij.codeInsight.completion.InsertHandler
import com.intellij.codeInsight.completion.PlainPrefixMatcher
import com.intellij.codeInsight.editorActions.TypedHandlerDelegate
import com.intellij.codeInsight.lookup.LookupElement
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiFile
import com.pannous.uniscript.Table
import com.pannous.uniscript.isNameChar

private const val MAX_COMPLETIONS = 1000 // the shortest first; typing on narrows and asks again
private const val BLOCK_TYPE_TEXT = "block"
private const val LONG_OPEN = "<:"
private const val SHORT_OPEN = "\\:"
private val NOT_IN_LONG_TAGS = "\n>[]{};=\"".toSet()

/** The typed content of the tag the caret is in: after `<:` (spaces allowed) or `\:` (a name), up to the caret */
private data class TypedTag(val content: String, val isShort: Boolean)

private fun typedTag(text: CharSequence, caret: Int): TypedTag? {
	var start = caret
	while (start > 0 && text[start - 1] !in NOT_IN_LONG_TAGS && text[start - 1] != ':') start--
	if (start < 2 || text[start - 1] != ':') return null
	val content = text.subSequence(start, caret).toString()
	return when (text[start - 2]) {
		'<' -> TypedTag(content, false).takeUnless { content.startsWith(' ') }
		'\\' -> TypedTag(content, true).takeIf { content.all(::isNameChar) }
		else -> null
	}
}

private val closeTag = InsertHandler<LookupElement> { context, _ ->
	val document = context.document
	val end = context.tailOffset
	if (end >= document.textLength || document.charsSequence[end] != '>') document.insertString(end, ">")
	context.editor.caretModel.moveToOffset(end + 1)
}

private val continueWithOperands = InsertHandler<LookupElement> { context, _ ->
	val end = context.tailOffset
	context.document.insertString(end, " ")
	context.editor.caretModel.moveToOffset(end + 1)
	AutoPopupController.getInstance(context.project).scheduleAutoPopup(context.editor)
}

/** The names of the index, read once: entities with their text, block words, and each block's operands */
private object Completions {
	val names = mutableListOf<Pair<String, String>>()
	val blocks = mutableListOf<String>()
	val operands = mutableMapOf<String, MutableList<Pair<String, String>>>()

	init {
		for ((key, text) in uniscript.index.entries(Table.NAMES)) {
			val space = key.indexOf(' ')
			when {
				space < 0 -> names += key to text
				space == key.lastIndex -> blocks += key.trimEnd()
				key[space + 1] != '*' -> operands.getOrPut(key.substring(0, space)) { mutableListOf() } += key.substring(space + 1) to text
			}
		}
	}
}

private fun shortestMatching(candidates: List<Pair<String, String>>, prefix: String) =
	candidates.asSequence().filter { it.first.startsWith(prefix, ignoreCase = true) }
		.sortedWith(compareBy({ it.first.length }, { it.first })).take(MAX_COMPLETIONS)

class UniscriptCompletionContributor : CompletionContributor(), DumbAware {
	override fun fillCompletionVariants(parameters: CompletionParameters, result: CompletionResultSet) {
		val tag = typedTag(parameters.editor.document.charsSequence, parameters.offset) ?: return
		val words = tag.content.split(' ')
		val prefix = words.last()
		val leading = words.dropLast(1)
		if (!leading.all(uniscript::isBlock)) return
		val matching = result.withPrefixMatcher(PlainPrefixMatcher(prefix))
		matching.restartCompletionOnAnyPrefixChange()
		val entities = leading.lastOrNull()?.let { Completions.operands[it] } ?: Completions.names
		val onItsOwn = leading.isEmpty() && !tag.isShort
		for ((name, text) in shortestMatching(entities, prefix)) {
			matching.addElement(LookupElementBuilder.create(name).withTypeText(text).withInsertHandler(closeTag.takeIf { onItsOwn }))
		}
		if (!tag.isShort) {
			Completions.blocks.filter { it.startsWith(prefix, ignoreCase = true) }.forEach {
				matching.addElement(LookupElementBuilder.create(it).withTypeText(BLOCK_TYPE_TEXT).withInsertHandler(continueWithOperands))
			}
		}
		matching.stopHere()
	}
}

class UniscriptTypedHandler : TypedHandlerDelegate() {
	override fun checkAutoPopup(charTyped: Char, project: Project, editor: Editor, file: PsiFile): Result {
		val caret = editor.caretModel.offset
		val opened = editor.document.charsSequence.subSequence(maxOf(0, caret - 1), caret).toString() + charTyped
		if (opened == LONG_OPEN || opened == SHORT_OPEN) AutoPopupController.getInstance(project).scheduleAutoPopup(editor)
		return Result.CONTINUE
	}
}
