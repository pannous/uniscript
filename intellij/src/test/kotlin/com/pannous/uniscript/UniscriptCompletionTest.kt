// Completion of entity names, block words and block operands inside uniscript tags, in any file type, and the
// Alt+Enter action replacing a tag with its Unicode
package com.pannous.uniscript

import com.intellij.codeInsight.lookup.LookupElementPresentation
import com.intellij.testFramework.fixtures.BasePlatformTestCase

private const val ENTER = '\n'
private const val TAB = '\t'

class UniscriptCompletionTest : BasePlatformTestCase() {
	private fun completions(text: String): List<String> {
		myFixture.configureByText("notes.txt", text)
		return myFixture.completeBasic()?.map { it.lookupString } ?: emptyList()
	}

	private fun choose(text: String, name: String, key: Char) {
		completions(text)
		myFixture.lookup.currentItem = myFixture.lookupElements!!.first { it.lookupString == name }
		myFixture.finishLookup(key)
	}

	fun testEntityNamesCompleteWithTheirCharacter() {
		myFixture.configureByText("notes.txt", "<:alph<caret>")
		val alpha = myFixture.completeBasic().first { it.lookupString == "alpha" }
		val presentation = LookupElementPresentation()
		alpha.renderElement(presentation)
		assertEquals("α", presentation.typeText)
	}

	fun testEnterInsertsTheCharacter() {
		choose("x <:alph<caret> y", "alpha", ENTER)
		myFixture.checkResult("x α<caret> y")
	}

	fun testTabKeepsTheNameAndClosesTheTag() {
		choose("<:alph<caret>", "alpha", TAB)
		myFixture.checkResult("<:alpha><caret>")
	}

	fun testShortTags() {
		choose("x \\:infin<caret> y", "infinity", TAB)
		myFixture.checkResult("x \\:infinity<caret> y")
		choose("x \\:infin<caret> y", "infinity", ENTER)
		myFixture.checkResult("x ∞<caret> y")
	}

	fun testOperandsOfTheBlockComplete() {
		assertTrue("seated-man" in completions("<:egyptian seated m<caret>"))
		choose("<:egyptian seated m<caret>", "seated-man", ENTER)
		myFixture.checkResult("𓀀<caret>")
	}

	fun testNamesSharingAPrefixFoldIntoAGroup() {
		val names = completions("\\:al<caret>")
		assertTrue(names.toString(), "alchemical-" in names)
		assertTrue(names.toString(), names.none { it.startsWith("alchemical-symbol") })
	}

	fun testBlockWordsCompleteAndAskForOperands() {
		completions("<:fractu<caret>") // the only match is inserted
		myFixture.checkResult("<:fracture <caret>")
	}

	fun testABlockWordShowsTheCharactersOfItsOperands() {
		myFixture.configureByText("notes.txt", "<:re<caret>")
		val red = myFixture.completeBasic().first { it.lookupString == "red" }
		val presentation = LookupElementPresentation()
		red.renderElement(presentation)
		assertEquals("🍎🔴🟥… 18", presentation.typeText)
	}

	fun testNothingOutsideTags() {
		assertEquals(emptyList<String>(), completions("alph<caret>"))
	}

	fun testAltEnterReplacesTheTag() {
		myFixture.configureByText("notes.txt", "x <:fracture <caret>A> y")
		myFixture.launchAction(myFixture.findSingleIntention("Replace with 𝔄"))
		myFixture.checkResult("x 𝔄 y")
	}
}
