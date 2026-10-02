// Alt+Enter on a uniscript tag: "Replace with α" puts its Unicode in place of the tag
package com.pannous.uniscript.ide

import com.intellij.codeInsight.intention.IntentionAction
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiFile

private const val FAMILY_NAME = "Replace uniscript with Unicode"

/** The tag under the caret (touching it from either side) with its Unicode, if it converts to any */
private fun tagAtCaret(editor: Editor): Pair<UniscriptTag, String>? {
	val caret = editor.caretModel.offset
	val tag = uniscriptTags(editor.document.charsSequence).firstOrNull { caret in it.range.startOffset..it.range.endOffset } ?: return null
	val unicode = tag.convert().getOrNull()?.text?.takeIf { it.isNotEmpty() } ?: return null
	return tag to unicode
}

class UniscriptToUnicodeIntention : IntentionAction, DumbAware {
	private var label = FAMILY_NAME

	override fun getText() = label

	override fun getFamilyName() = FAMILY_NAME

	override fun isAvailable(project: Project, editor: Editor?, file: PsiFile?): Boolean {
		val (_, unicode) = editor?.let(::tagAtCaret) ?: return false
		label = "Replace with $unicode"
		return true
	}

	override fun invoke(project: Project, editor: Editor?, file: PsiFile?) {
		val (tag, unicode) = editor?.let(::tagAtCaret) ?: return
		editor.document.replaceString(tag.range.startOffset, tag.range.endOffset, unicode)
	}

	override fun startInWriteAction() = true
}
