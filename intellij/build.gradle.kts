import org.jetbrains.intellij.platform.gradle.TestFrameworkType

plugins {
	id("org.jetbrains.kotlin.jvm") version "2.4.20"
	id("org.jetbrains.intellij.platform") version "2.19.0"
}

group = "com.pannous"
version = "0.1.0"

val entitiesIndex = rootDir.resolve("../data/entities.idx")
val platformLocalPath = providers.gradleProperty("platformLocalPath").get()

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
		ideaVersion {
			sinceBuild = "243"
			untilBuild = provider { null }
		}
	}
}

// the index shared with the Rust crate and the Swift package (data/entities.idx)
tasks.processResources { from(entitiesIndex) }
