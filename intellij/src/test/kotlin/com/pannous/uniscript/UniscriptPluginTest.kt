// The plugin in a headless IDE: highlighting, folding and the conversion actions in plain text and Java files
package com.pannous.uniscript

import com.intellij.lang.annotation.HighlightSeverity
import com.intellij.testFramework.EditorTestUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.pannous.uniscript.ide.BLOCK
import com.pannous.uniscript.ide.ENTITY
import com.pannous.uniscript.ide.MARKER
import com.pannous.uniscript.ide.OPERAND

private const val SAMPLE = "<:alpha> <:fracture A> \\:infinity <:nosuchthing> <:greek c>"

class UniscriptPluginTest : BasePlatformTestCase() {
	private fun highlighted(fileName: String, text: String) = myFixture.run {
		configureByText(fileName, text)
		doHighlighting().map { Triple(text.substring(it.startOffset, it.endOffset), it.severity, it.forcedTextAttributesKey ?: it.type.attributesKey) }
	}

	fun testTagsAreHighlightedInPlainText() {
		val infos = highlighted("notes.txt", SAMPLE)
		for (expected in listOf(
			Triple("<:", HighlightSeverity.INFORMATION, MARKER),
			Triple("alpha", HighlightSeverity.INFORMATION, ENTITY),
			Triple("fracture", HighlightSeverity.INFORMATION, BLOCK),
			Triple("A", HighlightSeverity.INFORMATION, OPERAND),
			Triple("infinity", HighlightSeverity.INFORMATION, ENTITY),
		)) assertTrue("$expected in $infos", expected in infos)
		val messages = myFixture.doHighlighting().map { it.severity to it.description }
		assertTrue(messages.toString(), HighlightSeverity.ERROR to "unknown uniscript entity: nosuchthing" in messages)
		assertTrue(messages.toString(), HighlightSeverity.WEAK_WARNING to "no greek form of c" in messages)
		assertTrue(messages.toString(), HighlightSeverity.INFORMATION to "𝔄" in messages)
	}

	fun testTagsAreHighlightedInCodeButScalaBoundsAreNoTags() {
		val infos = highlighted("Greek.java", "class Greek {} // <:pi> <T <: Bound[T]> <:nosuch x>")
		assertTrue(infos.toString(), Triple("pi", HighlightSeverity.INFORMATION, ENTITY) in infos)
		val errors = infos.filter { it.second == HighlightSeverity.ERROR }.map { it.first }
		assertEquals(listOf("<:nosuch x>"), errors)
	}

	fun testTagsFoldToTheirUnicode() {
		myFixture.configureByText("notes.txt", "$SAMPLE <:greek> a <:/greek>")
		EditorTestUtil.buildInitialFoldingsInBackground(myFixture.editor)
		val placeholders = myFixture.editor.foldingModel.allFoldRegions.map { it.placeholderText to it.isExpanded }
		assertEquals(listOf("α", "𝔄", "∞", "c").map { it to false }, placeholders)
	}

	fun testCodePointsAreHighlightedAndFolded() {
		val infos = highlighted("notes.txt", "\\U1F60D \\:U+1F60D <:0x1F60D> \\Users")
		for (entity in listOf("1F60D", "U+1F60D", "0x1F60D")) assertTrue(infos.toString(), Triple(entity, HighlightSeverity.INFORMATION, ENTITY) in infos)
		EditorTestUtil.buildInitialFoldingsInBackground(myFixture.editor)
		assertEquals(List(3) { "😍" }, myFixture.editor.foldingModel.allFoldRegions.map { it.placeholderText })
	}

	fun testActionsConvertTheSelectionOrTheFile() {
		myFixture.configureByText("notes.txt", "<:alpha> <selection><:fracture A></selection> \\:infinity")
		myFixture.performEditorAction("Uniscript.ToUnicode")
		myFixture.checkResult("<:alpha> 𝔄 \\:infinity")
		myFixture.editor.selectionModel.removeSelection()
		myFixture.performEditorAction("Uniscript.ToUnicode")
		myFixture.checkResult("α 𝔄 ∞")
		myFixture.performEditorAction("Uniscript.ToUniscript")
		myFixture.checkResult("<:alpha> <:fracture A> <:infinity>")
	}
}
