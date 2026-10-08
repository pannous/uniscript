// com.pannous:uniscript, the Rust core (c/ffi) for Java 22+ over the Foreign Function & Memory API.
// The jar bundles the native library of every platform under native/<rid>/, from `make -C ../c/ffi natives`;
// without them the host library of `make -C ../c/ffi` stands in for the host platform (development only).
plugins {
	`java-library`
	id("com.vanniktech.maven.publish") version "0.37.0"
}

val repositoryRoot = rootDir.parentFile
val cargoVersion = Regex("""^version = "(.+)"""", RegexOption.MULTILINE)
	.find(repositoryRoot.resolve("Cargo.toml").readText())!!.groupValues[1]
val nativeBuild = repositoryRoot.resolve("c/ffi/build")
val platforms = listOf("osx-arm64", "osx-x64", "linux-x64", "linux-arm64", "win-x64")
val bundledNatives = layout.buildDirectory.dir("natives")

group = "com.pannous"
version = cargoVersion

repositories { mavenCentral() }

tasks.withType<JavaCompile>().configureEach { options.release = 22 }

dependencies {
	testImplementation(platform("org.junit:junit-bom:5.13.4"))
	testImplementation("org.junit.jupiter:junit-jupiter")
	testRuntimeOnly("org.junit.platform:junit-platform-launcher")
	testImplementation("org.json:json:20250517")
}

fun hostPlatform(): String {
	val os = System.getProperty("os.name").lowercase()
	val arm = System.getProperty("os.arch") in listOf("aarch64", "arm64")
	val system = when {
		os.startsWith("mac") -> "osx"
		os.startsWith("windows") -> "win"
		else -> "linux"
	}
	return "$system-${if (arm) "arm64" else "x64"}"
}

val bundleNatives by tasks.registering(Sync::class) {
	description = "Copies the native libraries of c/ffi into native/<rid>/ of the jar"
	val host = hostPlatform()
	for (platform in platforms) {
		from(nativeBuild.resolve("natives/$platform")) { into("native/$platform") }
	}
	if (!nativeBuild.resolve("natives/$host").isDirectory) {
		from(nativeBuild) {
			include("libuniscript.dylib", "libuniscript.so", "uniscript.dll")
			into("native/$host")
		}
	}
	into(bundledNatives)
}

val checkNatives by tasks.registering {
	description = "Fails unless the jar bundles the native library of every platform (run before publishing)"
	val natives = bundledNatives
	val required = platforms
	dependsOn(bundleNatives)
	doLast {
		val missing = required.filter { natives.get().dir("native/$it").asFile.list().isNullOrEmpty() }
		check(missing.isEmpty()) { "no native library for $missing: run make -C c/ffi natives" }
	}
}

sourceSets.main { output.dir(mapOf("builtBy" to bundleNatives), bundledNatives) }

tasks.jar {
	manifest.attributes(
		"Automatic-Module-Name" to "com.pannous.uniscript.ffi",
		"Enable-Native-Access" to "ALL-UNNAMED",
		"Implementation-Version" to cargoVersion,
	)
}

// The host's native library built before the last change of the Rust sources or the index fails the shared cases: say so
val checkNativesCurrent by tasks.registering {
	description = "Fails when the host's native library of c/ffi is older than src/*.rs or data/entities.idx"
	val native = nativeBuild.resolve("natives/${hostPlatform()}").listFiles()?.firstOrNull()
	val inputs = repositoryRoot.resolve("src").listFiles { file -> file.extension == "rs" }.orEmpty().toList() + repositoryRoot.resolve("data/entities.idx")
	doLast {
		val newest = inputs.maxBy { it.lastModified() }
		check(native == null || native.lastModified() >= newest.lastModified()) { "$native is older than $newest: run make -C c/ffi natives" }
	}
}

tasks.test {
	dependsOn(checkNativesCurrent)
	useJUnitPlatform()
	jvmArgs("--enable-native-access=ALL-UNNAMED")
	systemProperty("uniscript.cases", repositoryRoot.resolve("js/test/cases.json").path)
	inputs.file(repositoryRoot.resolve("js/test/cases.json")) // a changed case file reruns the tests instead of reporting the cached success
	testLogging { events("failed"); exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL }
}

// Signing (required by Maven Central) with signingInMemoryKey(+Id, Password) or the gpg agent's key
// signing.gnupg.keyName from ~/.gradle/gradle.properties; unsigned without them (publishToMavenLocal)
val signingConfigured = listOf("signingInMemoryKey", "signing.gnupg.keyName", "signing.keyId")
	.any { providers.gradleProperty(it).isPresent }
if (providers.gradleProperty("signing.gnupg.keyName").isPresent) {
	apply(plugin = "signing")
	the<SigningExtension>().useGpgCmd()
}

tasks.javadoc { (options as StandardJavadocDocletOptions).addStringOption("Xdoclint:all,-missing", "-quiet") }

mavenPublishing {
	publishToMavenCentral(automaticRelease = false)
	if (signingConfigured) signAllPublications()
	coordinates("com.pannous", "uniscript", cargoVersion)
	pom {
		name = "uniscript"
		description = "ASCII names for Unicode text (<:alpha> → α, <:fracture A> → 𝔄) and back: the Rust core of uniscript for Java 22+ (FFM), with native libraries for macOS, Linux and Windows"
		url = "https://github.com/pannous/uniscript"
		inceptionYear = "2026"
		licenses {
			license {
				name = "MIT"
				url = "https://opensource.org/licenses/MIT"
			}
		}
		developers {
			developer {
				id = "pannous"
				name = "pannous"
				email = "info@pannous.com"
			}
		}
		scm {
			url = "https://github.com/pannous/uniscript"
			connection = "scm:git:https://github.com/pannous/uniscript.git"
			developerConnection = "scm:git:ssh://git@github.com/pannous/uniscript.git"
		}
	}
}
