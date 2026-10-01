// Installs com.pannous:uniscript-kotlin from the Maven repository given as -PuniscriptRepository (scripts/publish.sh)
plugins {
	id("org.jetbrains.kotlin.jvm") version "2.4.20"
	application
}

repositories {
	maven(url = providers.gradleProperty("uniscriptRepository").get())
	mavenCentral()
}

dependencies { implementation("com.pannous:uniscript-kotlin:${providers.gradleProperty("uniscriptVersion").get()}") }

kotlin { jvmToolchain(21) }

application { mainClass = "MainKt" }
