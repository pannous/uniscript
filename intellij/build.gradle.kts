import org.jetbrains.intellij.platform.gradle.IntelliJPlatformType
import org.jetbrains.intellij.platform.gradle.TestFrameworkType

plugins {
	id("org.jetbrains.kotlin.jvm") version "2.4.20"
	id("org.jetbrains.intellij.platform") version "2.19.0"
}

group = "com.pannous"
version = "0.2.0"

val entitiesIndex = rootDir.resolve("../data/entities.idx")
val platformLocalPath = providers.gradleProperty("platformLocalPath").get()
// the oldest IDE matching sinceBuild, checked by verifyPlugin next to the IDE compiled against
val verifyOldestVersion = providers.gradleProperty("verifyOldestVersion")
// secrets for publishPlugin and signPlugin come only from the environment, never from files in git
fun secret(name: String) = providers.environmentVariable(name)

repositories {
	mavenCentral()
	intellijPlatform { defaultRepositories() }
}

dependencies {
	intellijPlatform {
		if (file(platformLocalPath).exists()) local(platformLocalPath)
		else intellijIdea(providers.gradleProperty("platformVersion"))
		testFramework(TestFrameworkType.Platform)
	}
	testImplementation("junit:junit:4.13.2")
	testImplementation("org.opentest4j:opentest4j:1.3.0")
}

kotlin { jvmToolchain(21) }

intellijPlatform {
	buildSearchableOptions = false
	pluginConfiguration {
		id = "com.pannous.uniscript"
		name = "Uniscript"
		version = project.version.toString()
		vendor {
			name = "pannous"
			email = "info@pannous.com"
			url = "https://github.com/pannous/uniscript"
		}
		changeNotes = """
			<p>0.2.0: first release. Uniscript → Unicode and Unicode → Uniscript actions, highlighting of uniscript tags in
			every file type, folding of each tag to its Unicode.</p>
		""".trimIndent()
		ideaVersion {
			sinceBuild = "243"
			untilBuild = provider { null } // open-ended: the plugin uses only stable platform APIs
		}
	}
	pluginVerification {
		ides {
			current()
			create(IntelliJPlatformType.IntellijIdeaCommunity, verifyOldestVersion)
		}
	}
	signing {
		certificateChain = secret("CERTIFICATE_CHAIN")
		privateKey = secret("PRIVATE_KEY")
		password = secret("PRIVATE_KEY_PASSWORD")
	}
	publishing {
		token = secret("PUBLISH_TOKEN")
	}
}

// the index shared with the Rust crate and the Swift package (data/entities.idx)
tasks.processResources { from(entitiesIndex) }
