import java.io.FileInputStream
import java.util.Properties
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

// AGP 9 compiles Kotlin itself (built-in Kotlin); the separate
// org.jetbrains.kotlin.android plugin is rejected and must not be applied.
plugins {
    id("com.android.application")
}

// Release signing: reads a properties file kept OUTSIDE the repo
// (storeFile / storePassword / keyAlias / keyPassword), explicitly selected by
// JEV_KEYSTORE_PROPS. Without it, release builds are unsigned on every OS.
val releaseProps = Properties().apply {
    System.getenv("JEV_KEYSTORE_PROPS")?.takeIf { it.isNotBlank() }?.let { path ->
        val f = file(path)
        require(f.isFile) { "JEV_KEYSTORE_PROPS must point to an existing signing properties file" }
        FileInputStream(f).use { load(it) }
    }
}

android {
    namespace = "com.jev.probe"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.jev.probe"
        minSdk = 30
        targetSdk = 35
        // Fork versioning: versionName = upstream major.minor.<fork sequence>,
        // versionCode = upstream versionCode * 100 + fork sequence.
        versionCode = 511
        versionName = "1.4.11"

        // ML Kit's bundled Chinese recognizer ships native libs for every ABI.
        // The target phone (and every phone this can run on: minSdk 30) is
        // arm64, so keep only that one — the other three are dead weight.
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }

    signingConfigs {
        if (releaseProps.isNotEmpty()) {
            create("release") {
                storeFile = file(releaseProps.getProperty("storeFile"))
                storePassword = releaseProps.getProperty("storePassword")
                keyAlias = releaseProps.getProperty("keyAlias")
                keyPassword = releaseProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("release")
        }
    }

    // Uncompressed, page-aligned .so files: required for the 16 KB page-size
    // devices Android 15+ ships, and it lets the loader mmap the ML Kit natives
    // instead of unpacking them at install time.
    packaging {
        jniLibs {
            useLegacyPackaging = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

// Upstream's MIT NOTICE: redistributions keep LICENSE and NOTICE. Ship both
// inside the APK (assets/legal/), shown from Settings → 授權條款與聲明.
abstract class LegalAssets : DefaultTask() {
    @get:InputFiles
    abstract val legalFiles: ConfigurableFileCollection

    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    @TaskAction
    fun copy() {
        val out = outputDir.get().asFile.resolve("legal")
        out.deleteRecursively()
        out.mkdirs()
        legalFiles.forEach { it.copyTo(out.resolve(it.name), overwrite = true) }
    }
}

androidComponents {
    onVariants { variant ->
        val task = tasks.register<LegalAssets>("${variant.name}LegalAssets") {
            legalFiles.from(rootProject.file("LICENSE"), rootProject.file("NOTICE"))
        }
        variant.sources.assets?.addGeneratedSourceDirectory(task, LegalAssets::outputDir)
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.8.0")
    implementation("com.google.android.material:material:1.14.0")
    implementation("androidx.constraintlayout:constraintlayout:2.2.2")
    // On-device OCR. The *bundled* Chinese model (not the play-services variant):
    // it works on phones with no Google Play services and needs no model download.
    implementation("com.google.mlkit:text-recognition-chinese:16.0.1")
}
