// Completion of entity names, block words and block operands inside uniscript tags, in any file type
package com.pannous.uniscript

import com.intellij.codeInsight.lookup.LookupElementPresentation
import com.intellij.testFramework.fixtures.BasePlatformTestCase

class UniscriptCompletionTest : BasePlatformTestCase() {
	private fun completions(text: String): List<String> {
		myFixture.configureByText("notes.txt", text)
		return myFixture.completeBasic()?.map { it.lookupString } ?: emptyList()
	}

	fun testEntityNamesComplete() {
		val names = completions("<:alph<caret>")
		assertTrue(names.toString(), "alpha" in names)
	}

	fun testTheCharacterIsShownAndTheTagClosed() {
		myFixture.configureByText("notes.txt", "<:alph<caret>")
		val alpha = myFixture.completeBasic().first { it.lookupString == "alpha" }
		val presentation = LookupElementPresentation()
		alpha.renderElement(presentation)
		assertEquals("α", presentation.typeText)
		choose(alpha.lookupString)
		myFixture.checkResult("<:alpha><caret>")
	}

	private fun choose(name: String) {
		myFixture.lookup.currentItem = myFixture.lookupElements!!.first { it.lookupString == name }
		myFixture.finishLookup('\n')
	}

	fun testShortTagsStayOpen() {
		completions("x \\:infin<caret> y")
		choose("infinity")
		myFixture.checkResult("x \\:infinity<caret> y")
	}

	fun testOperandsOfTheBlockComplete() {
		val operands = completions("<:egyptian seated-m<caret>")
		assertTrue(operands.toString(), "seated-man" in operands)
	}

	fun testBlockWordsCompleteAndAskForOperands() {
		completions("<:fractu<caret>") // the only match is inserted
		myFixture.checkResult("<:fracture <caret>")
	}

	fun testNothingOutsideTags() {
		assertEquals(emptyList<String>(), completions("alph<caret>"))
	}
}
