// The Kotlin/JVM port of the Rust crate (src/lib.rs) as the library com.pannous:uniscript-kotlin
plugins {
	id("org.jetbrains.kotlin.jvm") version "2.4.20"
	id("com.vanniktech.maven.publish") version "0.37.0"
}

val cargoVersion = Regex("""(?m)^version = "(.+)"""").find(rootDir.resolve("../Cargo.toml").readText())!!.groupValues[1]
val entitiesIndex = rootDir.resolve("../data/entities.idx")
val sharedCases = rootDir.resolve("../js/test/cases.json")

group = "com.pannous"
version = cargoVersion

repositories { mavenCentral() }

dependencies {
	testImplementation(kotlin("test-junit"))
	testImplementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.9.0")
}

kotlin { jvmToolchain(21) }

// the index shared with the Rust crate and the Swift package (data/entities.idx)
tasks.processResources { from(entitiesIndex) }

tasks.test { systemProperty("uniscript.cases", sharedCases.absolutePath) }

// credentials (mavenCentralUsername, mavenCentralPassword, signingInMemoryKey…) come from ~/.gradle/gradle.properties
// or ORG_GRADLE_PROJECT_* environment variables, never from files in git; shared with com.pannous:uniscript (java/)
mavenPublishing {
	publishToMavenCentral(automaticRelease = false)
	if (providers.gradleProperty("signingInMemoryKey").isPresent || providers.gradleProperty("signing.keyId").isPresent) signAllPublications()
	coordinates("com.pannous", "uniscript-kotlin", cargoVersion)
	pom {
		name = "uniscript-kotlin"
		description = "Uniscript: a human readable, ASCII-only spelling of Unicode text (<:alpha> → α, <:fracture A> → 𝔄); pure Kotlin/JVM"
		url = "https://github.com/pannous/uniscript"
		inceptionYear = "2026"
		licenses {
			license {
				name = "MIT License"
				url = "https://opensource.org/licenses/MIT"
			}
		}
		developers {
			developer {
				id = "pannous"
				name = "pannous"
				email = "info@pannous.com"
				url = "https://github.com/pannous"
			}
		}
		scm {
			url = "https://github.com/pannous/uniscript"
			connection = "scm:git:https://github.com/pannous/uniscript.git"
			developerConnection = "scm:git:ssh://git@github.com/pannous/uniscript.git"
		}
	}
}
