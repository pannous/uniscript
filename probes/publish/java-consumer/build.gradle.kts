// Installs com.pannous:uniscript from the Maven repository given as -PuniscriptRepository (scripts/publish.sh)
plugins { application }

repositories {
	maven(url = providers.gradleProperty("uniscriptRepository").get())
	mavenCentral()
}

dependencies { implementation("com.pannous:uniscript:${providers.gradleProperty("uniscriptVersion").get()}") }

application {
	mainClass = "Consumer"
	applicationDefaultJvmArgs = listOf("--enable-native-access=ALL-UNNAMED")
}
