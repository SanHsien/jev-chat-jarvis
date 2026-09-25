package com.jev.probe.core

import android.content.Context
import android.util.Log

/**
 * App-private config store. Holds the three API routes (judge / reply / vision),
 * the relationship description used in Jev's state, the conversation whitelist,
 * plus the context (D stage) and OCR (B stage) switches.
 *
 * Key handling: stored in app-private SharedPreferences (not world-readable,
 * never logged, never in code/git). Only key *lengths* are ever logged.
 */
class Prefs(context: Context, prefsName: String = PREFS_MAIN) {

    private val sp = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)

    /**
     * Only the real config migrates — and only the real config logs it. The
     * throwaway instances behind the settings test buttons and the KB self-check
     * have nothing to carry over, and used to print one migration line per tap.
     */
    init { if (prefsName == PREFS_MAIN) { migrateIfNeeded(); dropRemovedVendors(); seedVercelDefaultIfFresh(); switchToSemiAutoOnce() } }

    /**
     * v1.2 -> v1.3: the single `openrouter_key` becomes the judge route's key.
     * `reply_model` keeps its old storage key, so it carries over untouched.
     */
    private fun migrateIfNeeded() {
        if (sp.getBoolean(K_MIGRATED_V13, false)) return   // runs exactly once
        val legacy = sp.getString(K_LEGACY_KEY, "") ?: ""
        val current = sp.getString(K_JUDGE_KEY, "") ?: ""
        val e = sp.edit().putBoolean(K_MIGRATED_V13, true)
        if (current.isBlank() && legacy.isNotBlank()) {
            e.putString(K_JUDGE_KEY, legacy)
            Log.i(TAG, "prefs migrated judgeKey.len=${legacy.length}")
        } else {
            Log.i(TAG, "prefs migrated judgeKey.len=${current.length} (no legacy key to copy)")
        }
        e.apply()
    }

    /**
     * Fork (SanHsien): the Bocha Jev, DeepSeek and DashScope / Qwen presets were
     * dropped (presets are limited to OpenRouter, Vercel, TypeSafe and OpenCode
     * Zen; see docs/DECISIONS.md). Runs exactly once: a
     * route still pointing at one of those hosts moves to Vercel AI Gateway and
     * loses its key (that key belongs to the removed vendor); a DeepSeek / Qwen
     * model left on a preset gateway becomes that gateway's default. A model on a
     * hand-typed custom host is the user's own choice and is left alone.
     */
    private fun dropRemovedVendors() {
        if (sp.getBoolean(K_DROPPED_VENDORS, false)) return
        val e = sp.edit().putBoolean(K_DROPPED_VENDORS, true)
        if (sp.getString(K_JUDGE_PROVIDER, null) == LEGACY_PROVIDER_BOCHA ||
            isRemovedHost(sp.getString(K_JUDGE_BASE, null))) {
            e.putString(K_JUDGE_PROVIDER, PROVIDER_VERCEL)
                .putString(K_JUDGE_BASE, DEFAULT_JUDGE_BASE_VERCEL)
                .putString(K_JUDGE_MODEL, DEFAULT_JUDGE_MODEL_VERCEL)
                .remove(K_JUDGE_KEY)
            Log.i(TAG, "prefs: judge route moved off a removed vendor to vercel")
        }
        dropRoute(e, K_REPLY_BASE, K_REPLY_KEY, K_REPLY_MODEL, DEFAULT_REPLY_BASE, DEFAULT_REPLY_MODEL, VERCEL_REPLY_MODEL)
        dropRoute(e, K_VISION_BASE, K_VISION_KEY, K_VISION_MODEL, DEFAULT_VISION_BASE, DEFAULT_VISION_MODEL, VERCEL_VISION_MODEL)
        e.apply()
    }

    private fun dropRoute(
        e: android.content.SharedPreferences.Editor,
        kBase: String, kKey: String, kModel: String,
        openRouterBase: String, openRouterModel: String, vercelModel: String,
    ) {
        val base = sp.getString(kBase, null)
        if (isRemovedHost(base)) {
            e.putString(kBase, VERCEL_OPENAI_BASE).putString(kModel, vercelModel).remove(kKey)
            Log.i(TAG, "prefs: $kBase moved off a removed vendor to vercel")
            return
        }
        if (!isRemovedModel(sp.getString(kModel, null))) return
        when ((base ?: openRouterBase).trim().trimEnd('/')) {
            openRouterBase -> e.putString(kModel, openRouterModel)
            VERCEL_OPENAI_BASE -> e.putString(kModel, vercelModel)
            else -> return
        }
        Log.i(TAG, "prefs: $kModel replaced a removed vendor's model")
    }

    /**
     * Fork (SanHsien): fresh installs default all three routes to Vercel AI Gateway,
     * so one gateway key covers judge, reply and vision. Runs exactly once and ONLY
     * on a truly empty config: no provider picked, no judge / legacy key, and the
     * reply / vision addresses never written. Anyone with an existing OpenRouter key
     * (upgraded or migrated) is left untouched. See docs/DIVERGENCE.md.
     */
    private fun seedVercelDefaultIfFresh() {
        if (sp.getBoolean(K_SEEDED_VERCEL, false)) return
        val e = sp.edit().putBoolean(K_SEEDED_VERCEL, true)
        val fresh = !sp.contains(K_JUDGE_PROVIDER) &&
            (sp.getString(K_JUDGE_KEY, "") ?: "").isBlank() &&
            (sp.getString(K_LEGACY_KEY, "") ?: "").isBlank() &&
            !sp.contains(K_REPLY_BASE) && !sp.contains(K_VISION_BASE)
        if (fresh) {
            e.putString(K_JUDGE_PROVIDER, PROVIDER_VERCEL)
                .putString(K_JUDGE_BASE, DEFAULT_JUDGE_BASE_VERCEL)
                .putString(K_JUDGE_MODEL, DEFAULT_JUDGE_MODEL_VERCEL)
                .putString(K_REPLY_BASE, VERCEL_OPENAI_BASE)
                .putString(K_REPLY_MODEL, VERCEL_REPLY_MODEL)
                .putString(K_VISION_BASE, VERCEL_OPENAI_BASE)
                .putString(K_VISION_MODEL, VERCEL_VISION_MODEL)
            Log.i(TAG, "prefs: fresh install seeded to vercel ai gateway")
        }
        e.apply()
    }

    /**
     * Fork (SanHsien): semi-automatic by default (docs/DECISIONS.md). A new message
     * from the other side only shows who would be analyzed plus an 「分析」 button;
     * stickers, photos and small talk no longer spend tokens on their own. Older
     * versions saved auto-analyze ON, so flip it off exactly once; turning it back
     * on in Settings afterwards sticks.
     */
    private fun switchToSemiAutoOnce() {
        if (sp.getBoolean(K_SEMI_AUTO, false)) return
        sp.edit().putBoolean(K_SEMI_AUTO, true).putBoolean(K_AUTO, false).apply()
    }

    // ---------------------------------------------------------------- judge

    /** "openrouter" | "typesafe" | "vercel" | "zen" | "custom". */
    var judgeProvider: String
        get() = sp.getString(K_JUDGE_PROVIDER, PROVIDER_OPENROUTER) ?: PROVIDER_OPENROUTER
        set(v) = sp.edit().putString(K_JUDGE_PROVIDER, v.trim()).apply()

    /** Host root; the path is appended per provider (see [judgeEndpoint]). */
    var judgeBaseUrl: String
        get() = sp.getString(K_JUDGE_BASE, DEFAULT_JUDGE_BASE_OPENROUTER) ?: DEFAULT_JUDGE_BASE_OPENROUTER
        set(v) = sp.edit().putString(K_JUDGE_BASE, v.trim()).apply()

    var judgeKey: String
        get() = sp.getString(K_JUDGE_KEY, "") ?: ""
        set(v) = sp.edit().putString(K_JUDGE_KEY, v.trim()).apply()

    var judgeModel: String
        get() = sp.getString(K_JUDGE_MODEL, DEFAULT_JUDGE_MODEL_OPENROUTER) ?: DEFAULT_JUDGE_MODEL_OPENROUTER
        set(v) = sp.edit().putString(K_JUDGE_MODEL, v.trim()).apply()

    /** Back-compat alias so older call sites keep compiling. */
    var openRouterKey: String
        get() = judgeKey
        set(v) { judgeKey = v }

    // ---------------------------------------------------------------- reply

    /** OpenAI-compatible base, up to and including `/v1`. */
    var replyBaseUrl: String
        get() = sp.getString(K_REPLY_BASE, DEFAULT_REPLY_BASE) ?: DEFAULT_REPLY_BASE
        set(v) = sp.edit().putString(K_REPLY_BASE, v.trim()).apply()

    /** Blank = fall back to [judgeKey]. */
    var replyKey: String
        get() = sp.getString(K_REPLY_KEY, "") ?: ""
        set(v) = sp.edit().putString(K_REPLY_KEY, v.trim()).apply()

    /** Generative model for drafting the 3 candidate replies. */
    var replyModel: String
        get() = sp.getString(K_REPLY_MODEL, DEFAULT_REPLY_MODEL) ?: DEFAULT_REPLY_MODEL
        set(v) = sp.edit().putString(K_REPLY_MODEL, v.trim()).apply()

    // --------------------------------------------------------------- vision

    /**
     * Blank = the OpenRouter vision default. Deliberately does NOT follow
     * [replyBaseUrl]: a text-only reply host has no vision endpoint, so
     * inheriting it would silently break OCR.
     */
    var visionBaseUrl: String
        get() = sp.getString(K_VISION_BASE, DEFAULT_VISION_BASE) ?: DEFAULT_VISION_BASE
        set(v) = sp.edit().putString(K_VISION_BASE, v.trim()).apply()

    /** Blank = fall back to [replyKey] then [judgeKey]. */
    var visionKey: String
        get() = sp.getString(K_VISION_KEY, "") ?: ""
        set(v) = sp.edit().putString(K_VISION_KEY, v.trim()).apply()

    var visionModel: String
        get() = sp.getString(K_VISION_MODEL, DEFAULT_VISION_MODEL) ?: DEFAULT_VISION_MODEL
        set(v) = sp.edit().putString(K_VISION_MODEL, v.trim()).apply()

    // -------------------------------------------------------- context (D)

    /**
     * Record per-contact history and inject it into analysis. Default OFF:
     * nothing about the user's chats is written to disk unless they opt in
     * (v1.3 revision, D stage).
     */
    var contextEnabled: Boolean
        get() = sp.getBoolean(K_CTX_ENABLED, false)
        set(v) = sp.edit().putBoolean(K_CTX_ENABLED, v).apply()

    /** How many recent history entries to inject. */
    var contextHistoryCount: Int
        get() = sp.getInt(K_CTX_COUNT, 30)
        set(v) = sp.edit().putInt(K_CTX_COUNT, v).apply()

    /** Auto-summarize a contact once enough history accumulates. */
    var autoSummary: Boolean
        get() = sp.getBoolean(K_AUTO_SUMMARY, true)
        set(v) = sp.edit().putBoolean(K_AUTO_SUMMARY, v).apply()

    // ------------------------------------------------------------ OCR (B)

    /** "mlkit" | "vision". */
    var ocrEngine: String
        get() = sp.getString(K_OCR_ENGINE, OCR_MLKIT) ?: OCR_MLKIT
        set(v) = sp.edit().putString(K_OCR_ENGINE, v.trim()).apply()

    /** Run generic OCR capture on apps with no dedicated adapter. */
    var ocrForUnknownApps: Boolean
        get() = sp.getBoolean(K_OCR_UNKNOWN, true)
        set(v) = sp.edit().putBoolean(K_OCR_UNKNOWN, v).apply()

    /** Fall back to OCR when an adapted app's node tree comes back empty. */
    var ocrFallback: Boolean
        get() = sp.getBoolean(K_OCR_FALLBACK, true)
        set(v) = sp.edit().putBoolean(K_OCR_FALLBACK, v).apply()

    /** Auto-analyze in OCR mode (default off: OCR costs a screenshot each time). */
    var ocrAutoAnalyze: Boolean
        get() = sp.getBoolean(K_OCR_AUTO, false)
        set(v) = sp.edit().putBoolean(K_OCR_AUTO, v).apply()

    // ------------------------------------------------------------- existing

    /** Free-text describing who the other person is; goes into Jev's state. */
    var relationship: String
        get() = sp.getString(K_REL, DEFAULT_REL) ?: DEFAULT_REL
        set(v) = sp.edit().putString(K_REL, v).apply()

    /** Master on/off for showing the overlay + running analysis. */
    var enabled: Boolean
        get() = sp.getBoolean(K_ENABLED, true)
        set(v) = sp.edit().putBoolean(K_ENABLED, v).apply()

    /**
     * Conversation whitelist: titles the assistant is allowed to act on. Empty
     * set means "all conversations". Stored as a plain string set.
     */
    var whitelist: Set<String>
        get() = sp.getStringSet(K_WHITELIST, emptySet()) ?: emptySet()
        set(v) = sp.edit().putStringSet(K_WHITELIST, v).apply()

    /** Overlay panel opacity, 60..100 (%). Lower lets the chat show through. */
    var overlayOpacity: Int
        get() = sp.getInt(K_OPACITY, 92).coerceIn(60, 100)
        set(v) = sp.edit().putInt(K_OPACITY, v.coerceIn(60, 100)).apply()

    /** Remembered vertical position of the bubble (px); -1 = default. */
    var bubbleY: Int
        get() = sp.getInt(K_BUBBLE_Y, -1)
        set(v) = sp.edit().putInt(K_BUBBLE_Y, v).apply()

    /** Remembered horizontal position of the bubble (px); -1 = default. */
    var bubbleX: Int
        get() = sp.getInt(K_BUBBLE_X, -1)
        set(v) = sp.edit().putInt(K_BUBBLE_X, v).apply()

    /**
     * Auto-analyze on every incoming message. Default false (semi-automatic): the
     * overlay names the person and waits for a tap on 「分析」.
     */
    var autoAnalyze: Boolean
        get() = sp.getBoolean(K_AUTO, false)
        set(v) = sp.edit().putBoolean(K_AUTO, v).apply()

    // ------------------------------------------------------------- helpers

    /** Reply route key, falling back to the judge key. */
    fun effectiveReplyKey(): String = replyKey.ifBlank { judgeKey }

    /** Vision route key, falling back to reply then judge. */
    fun effectiveVisionKey(): String = visionKey.ifBlank { effectiveReplyKey() }

    /** Full POST URL for the Jev decisions call, per provider. */
    fun judgeEndpoint(): String {
        val base = judgeBaseUrl.trim().trimEnd('/')
        return when (judgeProvider) {
            PROVIDER_TYPESAFE -> "$base/v1/systemone"
            PROVIDER_VERCEL -> "$base/v1/systemone"   // TypeSafe-compatible gateway
            PROVIDER_ZEN -> "$base/v1/systemone"      // TypeSafe-compatible gateway
            PROVIDER_CUSTOM -> judgeBaseUrl.trim()   // user supplies the full URL
            else -> "$base/alpha/decisions"
        }
    }

    /** Full POST URL for the OpenAI-compatible chat completions call. */
    fun replyEndpoint(): String = "${replyBaseUrl.trim().trimEnd('/')}/chat/completions"

    /** Same shape as [replyEndpoint]; blank falls back to the OpenRouter default. */
    fun visionEndpoint(): String {
        val base = visionBaseUrl.trim().ifBlank { DEFAULT_VISION_BASE }
        return "${base.trimEnd('/')}/chat/completions"
    }

    fun isAllowed(title: String?): Boolean {
        val wl = whitelist
        if (wl.isEmpty()) return true
        if (title == null) return false
        return wl.any { title.contains(it) }
    }

    /** Readiness gate: the judge route is the one that must be configured. */
    fun hasKey(): Boolean = judgeKey.isNotBlank()

    companion object {
        private const val TAG = "JEVASSIST"

        /** The one real config file. Anything else is a scratch instance. */
        const val PREFS_MAIN = "jev_assistant"

        private const val K_LEGACY_KEY = "openrouter_key"
        private const val K_MIGRATED_V13 = "prefs_migrated_v13"
        private const val K_SEEDED_VERCEL = "fork_seeded_vercel_v1"
        private const val K_DROPPED_VENDORS = "fork_dropped_cn_vendors_v1"
        private const val K_SEMI_AUTO = "fork_semi_auto_v1"
        private const val K_JUDGE_PROVIDER = "judge_provider"
        private const val K_JUDGE_BASE = "judge_base_url"
        private const val K_JUDGE_KEY = "judge_key"
        private const val K_JUDGE_MODEL = "judge_model"
        private const val K_REPLY_BASE = "reply_base_url"
        private const val K_REPLY_KEY = "reply_key"
        private const val K_REPLY_MODEL = "reply_model"
        private const val K_VISION_BASE = "vision_base_url"
        private const val K_VISION_KEY = "vision_key"
        private const val K_VISION_MODEL = "vision_model"
        private const val K_CTX_ENABLED = "context_enabled"
        private const val K_CTX_COUNT = "context_history_count"
        private const val K_AUTO_SUMMARY = "auto_summary"
        private const val K_OCR_ENGINE = "ocr_engine"
        private const val K_OCR_UNKNOWN = "ocr_unknown_apps"
        private const val K_OCR_FALLBACK = "ocr_fallback"
        private const val K_OCR_AUTO = "ocr_auto_analyze"
        private const val K_REL = "relationship"
        private const val K_ENABLED = "enabled"
        private const val K_WHITELIST = "whitelist"
        private const val K_OPACITY = "overlay_opacity"
        private const val K_BUBBLE_Y = "bubble_y"
        private const val K_BUBBLE_X = "bubble_x"
        private const val K_AUTO = "auto_analyze"

        const val PROVIDER_OPENROUTER = "openrouter"
        const val PROVIDER_TYPESAFE = "typesafe"
        const val PROVIDER_VERCEL = "vercel"
        const val PROVIDER_ZEN = "zen"
        const val PROVIDER_CUSTOM = "custom"

        const val OCR_MLKIT = "mlkit"
        const val OCR_VISION = "vision"

        // Judge route presets.
        const val DEFAULT_JUDGE_BASE_OPENROUTER = "https://openrouter.ai/api"
        const val DEFAULT_JUDGE_MODEL_OPENROUTER = "typesafe/jev-1.13"
        const val DEFAULT_JUDGE_BASE_TYPESAFE = "https://api.typesafe.ai"
        const val DEFAULT_JUDGE_MODEL_TYPESAFE = "jev-latest"
        // Vercel AI Gateway's TypeSafe-compatible API. Same /v1/systemone body
        // and noul answers as TypeSafe direct; model id is the gateway's.
        const val DEFAULT_JUDGE_BASE_VERCEL = "https://ai-gateway.vercel.sh/typesafe"
        const val DEFAULT_JUDGE_MODEL_VERCEL = "typesafe-ai/jev"
        // OpenCode Zen's TypeSafe-compatible API. Same /v1/systemone body and
        // noul answers; jev-1.13 is free on output ($0.042/M input, ~1k tokens
        // per judgment), jev-1.13-free is fully free but capability-limited.
        const val DEFAULT_JUDGE_BASE_ZEN = "https://opencode.ai/zen"
        const val DEFAULT_JUDGE_MODEL_ZEN = "jev-1.13"

        // Reply route presets (OpenAI-compatible chat completions).
        const val DEFAULT_REPLY_BASE = "https://openrouter.ai/api/v1"
        const val DEFAULT_REPLY_MODEL = "google/gemini-2.5-flash"

        // Fork (SanHsien): Vercel AI Gateway's OpenAI-compatible API, for the reply
        // and vision routes, so the judge route's gateway key works for all three.
        const val VERCEL_OPENAI_BASE = "https://ai-gateway.vercel.sh/v1"
        const val VERCEL_REPLY_MODEL = "google/gemini-2.5-flash"
        const val VERCEL_VISION_MODEL = "google/gemini-2.5-flash"

        // Vision route preset (user may change).
        const val DEFAULT_VISION_BASE = "https://openrouter.ai/api/v1"
        const val DEFAULT_VISION_MODEL = "google/gemini-2.5-flash"

        // Fork (SanHsien): presets dropped from this fork (see docs/DECISIONS.md).
        // Only used to migrate configs saved by older versions.
        private const val LEGACY_PROVIDER_BOCHA = "bocha"
        private val REMOVED_HOSTS = listOf("bocha.cn", "deepseek.com", "aliyuncs.com")
        private val REMOVED_MODELS = listOf("deepseek", "qwen")

        fun isRemovedHost(url: String?): Boolean =
            url != null && REMOVED_HOSTS.any { url.contains(it, ignoreCase = true) }

        fun isRemovedModel(model: String?): Boolean =
            model != null && REMOVED_MODELS.any { model.contains(it, ignoreCase = true) }

        const val DEFAULT_REL = "對方是我的伴侶；from=me 的是我發的，from=other 的是對方發的"
    }
}
