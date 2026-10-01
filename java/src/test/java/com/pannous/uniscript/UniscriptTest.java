package com.pannous.uniscript;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/** The Java API beyond the shared cases */
class UniscriptTest {
	@Test
	void convertsBothWays() {
		assertEquals("α 𝔄", Uniscript.toUnicode("<:alpha> <:fracture A>"));
		assertEquals("<:alpha> <:fracture A>", Uniscript.toUniscript("α 𝔄"));
	}

	@Test
	void toUnicodeIsLenient() {
		assertEquals("α <:nosuchthing>", Uniscript.toUnicode("<:alpha> <:nosuchthing>"));
	}

	@Test
	void errorsCarryKindAndMessage() {
		UniscriptException error = assertThrows(UniscriptException.class,
				() -> Uniscript.convert("<:nosuchthing>", Uniscript.Mode.WARN));
		assertEquals(UniscriptException.Kind.UNKNOWN_ENTITY, error.kind());
		assertEquals("unknown uniscript entity: nosuchthing", error.getMessage());
	}

	@Test
	void metaTemplates() {
		assertEquals("color: {}", Uniscript.metaTemplate("color").orElseThrow());
		assertEquals(true, Uniscript.metaTemplate("nosuchkey").isEmpty());
	}

	@Test
	void runsOnManyThreads() throws InterruptedException {
		Thread[] threads = new Thread[8];
		for (int index = 0; index < threads.length; index++) {
			threads[index] = Thread.ofVirtual().start(() -> {
				for (int round = 0; round < 200; round++) assertEquals("𝔄", Uniscript.toUnicode("<:fracture A>"));
			});
		}
		for (Thread thread : threads) thread.join();
	}
}
