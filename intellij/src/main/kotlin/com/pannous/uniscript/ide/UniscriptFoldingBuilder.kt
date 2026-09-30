// Shows each uniscript tag as its Unicode (`<:fracture A>` as 𝔄); the tag unfolds when the caret enters it
package com.pannous.uniscript.ide

import com.intellij.lang.ASTNode
import com.intellij.lang.folding.FoldingBuilderEx
import com.intellij.lang.folding.FoldingDescriptor
import com.intellij.openapi.editor.Document
import com.intellij.openapi.project.DumbAware
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile

private const val UNKNOWN_PLACEHOLDER = "…"

class UniscriptFoldingBuilder : FoldingBuilderEx(), DumbAware {
	override fun buildFoldRegions(root: PsiElement, document: Document, quick: Boolean): Array<FoldingDescriptor> {
		if (root !is PsiFile || !isScannedFile(root)) return FoldingDescriptor.EMPTY_ARRAY
		return uniscriptTags(document.charsSequence).mapNotNull { tag ->
			val unicode = tag.convert().getOrNull()?.text?.takeIf { it.isNotEmpty() } ?: return@mapNotNull null
			FoldingDescriptor(root.node, tag.range, null, unicode)
		}.toList().toTypedArray()
	}

	override fun getPlaceholderText(node: ASTNode) = UNKNOWN_PLACEHOLDER

	override fun isCollapsedByDefault(node: ASTNode) = true
}
