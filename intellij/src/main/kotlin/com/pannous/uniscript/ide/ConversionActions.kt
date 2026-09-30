// Edit | Uniscript: convert the selection, or the whole file, between uniscript and Unicode
package com.pannous.uniscript.ide

import com.intellij.codeInsight.hint.HintManager
import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.project.DumbAwareAction
import com.intellij.openapi.util.TextRange
import com.pannous.uniscript.Converted
import com.pannous.uniscript.UniscriptError

abstract class ConversionAction : DumbAwareAction() {
	abstract fun convert(text: String): Converted

	override fun getActionUpdateThread() = ActionUpdateThread.BGT

	override fun update(event: AnActionEvent) {
		event.presentation.isEnabledAndVisible = event.getData(CommonDataKeys.EDITOR)?.document?.isWritable == true
	}

	override fun actionPerformed(event: AnActionEvent) {
		val editor = event.getData(CommonDataKeys.EDITOR) ?: return
		val selection = editor.selectionModel
		val range = if (selection.hasSelection()) TextRange(selection.selectionStart, selection.selectionEnd)
		else TextRange(0, editor.document.textLength)
		val converted = try {
			convert(editor.document.getText(range))
		} catch (error: UniscriptError) {
			return HintManager.getInstance().showErrorHint(editor, error.message ?: "invalid uniscript")
		}
		WriteCommandAction.runWriteCommandAction(event.project, templateText, null, {
			editor.document.replaceString(range.startOffset, range.endOffset, converted.text)
		})
		if (converted.warnings.isNotEmpty()) {
			HintManager.getInstance().showInformationHint(editor, converted.warnings.joinToString("\n") { it.toString() })
		}
	}
}

class ToUnicodeAction : ConversionAction() {
	override fun convert(text: String) = uniscript.convert(text)
}

class ToUniscriptAction : ConversionAction() {
	override fun convert(text: String) = Converted(uniscript.toUniscript(text), emptyList())
}
