// Completion inside uniscript tags in every file type: entity names after `<:` and `\:`, block words, and after block
// words their operands (`<:egyptian seated m` → seated-man). Names sharing their next segment fold into one group
// (`alchemical-`). Enter puts the character in place of the tag, Tab keeps the name. The popup opens after `<:` and `\:`.
package com.pannous.uniscript.ide

import com.intellij.codeInsight.AutoPopupController
import com.intellij.codeInsight.completion.CompletionContributor
import com.intellij.codeInsight.completion.CompletionParameters
import com.intellij.codeInsight.completion.CompletionResultSet
import com.intellij.codeInsight.completion.InsertHandler
import com.intellij.codeInsight.completion.InsertionContext
import com.intellij.codeInsight.completion.PlainPrefixMatcher
import com.intellij.codeInsight.editorActions.TypedHandlerDelegate
import com.intellij.codeInsight.lookup.Lookup
import com.intellij.codeInsight.lookup.LookupElement
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiFile
import com.pannous.uniscript.Table
import com.pannous.uniscript.isNameChar

private const val MAX_COMPLETIONS = 1000 // the shortest first; typing on narrows and asks again
private const val GROUP_SAMPLES = 3 // characters shown beside a group of names
private const val BLOCK_TYPE_TEXT = "block" // a block word without operands of its own (mirror)
private const val SEGMENT_END = '-'
private const val TAG_END = '>'
private const val LONG_OPEN = "<:"
private const val SHORT_OPEN = "\\:"
private val NOT_IN_LONG_TAGS = "\n>[]{};=\"".toSet()

/** The tag the caret is typing in: its marker's offset and the content after `<:` (words) or `\:` (a name) */
private data class TypedTag(val start: Int, val content: String, val isShort: Boolean)

private fun typedTag(text: CharSequence, caret: Int): TypedTag? {
	var start = caret
	while (start > 0 && text[start - 1] !in NOT_IN_LONG_TAGS && text[start - 1] != ':') start--
	if (start < 2 || text[start - 1] != ':') return null
	val content = text.subSequence(start, caret).toString()
	return when (text[start - 2]) {
		'<' -> TypedTag(start - 2, content, false).takeUnless { content.startsWith(' ') }
		'\\' -> TypedTag(start - 2, content, true).takeIf { content.all(::isNameChar) }
		else -> null
	}
}

private fun reopenPopup(context: InsertionContext) = AutoPopupController.getInstance(context.project).scheduleAutoPopup(context.editor)

/** Enter: the whole tag becomes its Unicode; Tab: the name stays, an entity on its own closes its tag */
private fun finishName(context: InsertionContext, closes: Boolean) {
	val document = context.document
	val end = context.tailOffset
	val tag = typedTag(document.charsSequence, end) ?: return
	val closed = end < document.textLength && document.charsSequence[end] == TAG_END
	if (context.completionChar == Lookup.NORMAL_SELECT_CHAR) {
		val written = document.getText(TextRange(tag.start, end)) + if (tag.isShort) "" else TAG_END
		val unicode = runCatching { uniscript.convert(written).text }.getOrNull()?.takeIf { it.isNotEmpty() }
		if (unicode != null) {
			document.replaceString(tag.start, if (closed && !tag.isShort) end + 1 else end, unicode)
			return context.editor.caretModel.moveToOffset(tag.start + unicode.length)
		}
	}
	if (!closes) return
	if (!closed) document.insertString(end, TAG_END.toString())
	context.editor.caretModel.moveToOffset(end + 1)
}

private val continueWithOperands = InsertHandler<LookupElement> { context, _ ->
	val end = context.tailOffset
	context.document.insertString(end, " ")
	context.editor.caretModel.moveToOffset(end + 1)
	reopenPopup(context)
}

/** The names of the index, read once: entities with their text, block words, and each block's operands */
private object Completions {
	val names = mutableListOf<Pair<String, String>>()
	val blocks = mutableSetOf<String>()
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

/** A name, or a group of names sharing everything up to the "-" ending `name` (`size` > 1) */
private data class Completion(val name: String, val text: String, val size: Int)

private val shortestFirst = compareBy<Pair<String, String>>({ it.first.length }, { it.first })

/** `🍎🔴🟥… 18`: the characters of the shortest names, and how many there are */
private fun summary(members: List<Pair<String, String>>) =
	members.sortedWith(shortestFirst).take(GROUP_SAMPLES).joinToString("") { it.second } + "… ${members.size}"

/** The candidates starting with prefix (ignoring case), the shortest first; names sharing their next segment fold into
 *  one group, as deep as all of them agree */
private fun grouped(candidates: List<Pair<String, String>>, prefix: String): List<Completion> {
	val matching = candidates.filter { it.first.startsWith(prefix, ignoreCase = true) }
	var start = prefix.length
	while (true) {
		val groups = matching.groupBy { (name, _) -> name.indexOf(SEGMENT_END, start).let { if (it < 0) name else name.substring(0, it + 1) } }
		if (groups.size == 1 && matching.size > 1) {
			start = groups.keys.single().length
			continue
		}
		return groups.map { (key, members) ->
			members.singleOrNull()?.let { Completion(it.first, it.second, 1) }
				?: Completion(key, summary(members), members.size)
		}.sortedWith(compareBy({ it.name.length }, { it.name })).take(MAX_COMPLETIONS)
	}
}

class UniscriptCompletionContributor : CompletionContributor(), DumbAware {
	override fun fillCompletionVariants(parameters: CompletionParameters, result: CompletionResultSet) {
		val tag = typedTag(parameters.editor.document.charsSequence, parameters.offset) ?: return
		val words = tag.content.split(' ')
		val leading = words.dropLast(1).takeWhile { it in Completions.blocks }
		// spaces between the operand's words stand for hyphens: the same length, so the replaced text stays right
		val prefix = words.drop(leading.size).joinToString(SEGMENT_END.toString())
		val matching = result.withPrefixMatcher(PlainPrefixMatcher(prefix))
		matching.restartCompletionOnAnyPrefixChange()
		val candidates = if (leading.isEmpty()) Completions.names else Completions.operands[leading.last()] ?: emptyList()
		val closes = leading.isEmpty() && !tag.isShort
		for ((name, text, size) in grouped(candidates, prefix)) {
			val element = LookupElementBuilder.create(name).withTypeText(text)
			matching.addElement(element.withInsertHandler { context, _ -> if (size > 1) reopenPopup(context) else finishName(context, closes) })
		}
		if (!tag.isShort && leading.isEmpty()) {
			// a block word is the group of its operands: <:red> shows 🍎🔴🟥… 18 and asks for them when chosen
			Completions.blocks.filter { it.startsWith(prefix, ignoreCase = true) }.forEach { block ->
				val typeText = Completions.operands[block]?.let(::summary) ?: BLOCK_TYPE_TEXT
				matching.addElement(LookupElementBuilder.create(block).withTypeText(typeText).withInsertHandler(continueWithOperands))
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
