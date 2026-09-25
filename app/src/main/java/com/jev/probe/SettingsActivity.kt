package com.jev.probe

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.util.Log
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.jev.probe.core.ChatSnapshot
import com.jev.probe.core.Msg
import com.jev.probe.core.Prefs
import com.jev.probe.core.kb.KbSelfCheck
import com.jev.probe.core.kb.KbStore
import com.jev.probe.jev.JudgeClient
import com.jev.probe.jev.ReplyClient
import com.jev.probe.jev.VisionClient
import java.util.concurrent.Executors
import kotlin.math.roundToInt

class SettingsActivity : AppCompatActivity() {

    private lateinit var prefs: Prefs
    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())

    private val accent = Color.parseColor("#3A7AFE")
    private val ink = Color.parseColor("#111827")
    private val sub = Color.parseColor("#6B7280")
    private val pillOff = Color.parseColor("#EEF1F5")

    /** Selected provider index per card, held so Save can read it back. */
    private var judgeProviderIdx = 0

    private fun dp(v: Int) = TypedValue.applyDimension(
        TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics).roundToInt()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        Log.i(TAG, "settings opened judgeKey.len=${prefs.judgeKey.length}" +
            " replyKey.len=${prefs.replyKey.length} visionKey.len=${prefs.visionKey.length}")
        window.decorView.setBackgroundColor(Color.parseColor("#F2F3F5"))

        val scroll = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(28))
        }
        root.padForSystemBars()   // edge-to-edge: keep the title off the status bar
        scroll.addView(root)

        root.addView(header("設定"))

        // =================== 接口 ===================
        root.addView(section("接口"))

        // --- 判斷接口（Jev） ---
        val judgeCard = card()
        judgeCard.addView(cardTitle("判斷接口（Jev）"))
        judgeCard.addView(text("讀對方訊息、給意圖判斷和候選排序。必須配置。", 12f, sub))

        val judgeBaseEdit = edit(prefs.judgeBaseUrl, Prefs.DEFAULT_JUDGE_BASE_OPENROUTER)
        val judgeModelEdit = edit(prefs.judgeModel, Prefs.DEFAULT_JUDGE_MODEL_OPENROUTER)
        judgeProviderIdx = when (prefs.judgeProvider) {
            Prefs.PROVIDER_OPENROUTER -> 0
            Prefs.PROVIDER_TYPESAFE -> 1
            Prefs.PROVIDER_VERCEL -> 2
            Prefs.PROVIDER_ZEN -> 3
            Prefs.PROVIDER_CUSTOM -> 4
            else -> 0
        }
        judgeCard.addView(pills(
            listOf("OpenRouter", "TypeSafe 直連", "Vercel", "OpenCode Zen", "自定義"), judgeProviderIdx) { idx ->
            judgeProviderIdx = idx
            when (idx) {
                0 -> {
                    judgeBaseEdit.setText(Prefs.DEFAULT_JUDGE_BASE_OPENROUTER)
                    judgeModelEdit.setText(Prefs.DEFAULT_JUDGE_MODEL_OPENROUTER)
                }
                1 -> {
                    judgeBaseEdit.setText(Prefs.DEFAULT_JUDGE_BASE_TYPESAFE)
                    judgeModelEdit.setText(Prefs.DEFAULT_JUDGE_MODEL_TYPESAFE)
                }
                2 -> {
                    judgeBaseEdit.setText(Prefs.DEFAULT_JUDGE_BASE_VERCEL)
                    judgeModelEdit.setText(Prefs.DEFAULT_JUDGE_MODEL_VERCEL)
                }
                3 -> {
                    judgeBaseEdit.setText(Prefs.DEFAULT_JUDGE_BASE_ZEN)
                    judgeModelEdit.setText(Prefs.DEFAULT_JUDGE_MODEL_ZEN)
                }
                // Custom POSTs the box verbatim, so a preset HOST left in the box
                // would hit the API root. Expand it into the full endpoint the
                // preset would have used; anything hand-typed is left alone.
                4 -> judgeBaseEdit.setText(expandJudgeUrl(judgeBaseEdit.text.toString()))
            }
        })
        judgeCard.addView(label("Base URL"))
        judgeCard.addView(judgeBaseEdit)
        judgeCard.addView(text("OpenRouter 拼 /alpha/decisions；TypeSafe / Vercel / OpenCode Zen 拼 /v1/systemone；自定義按原樣 POST。Vercel 用 AI Gateway 的金鑰，OpenCode Zen 用 Zen 的金鑰。",
            11f, sub))
        judgeCard.addView(label("金鑰"))
        judgeCard.addView(edit(prefs.judgeKey, "sk-...", password = true).also { judgeKeyEdit = it })
        judgeCard.addView(label("模型"))
        judgeCard.addView(judgeModelEdit)
        val judgeResult = resultText()
        judgeCard.addView(cardBtn("測試判斷") {
            val base = judgeBaseEdit.text.toString().trim()
            val key = judgeKeyEdit.text.toString().trim()
            val model = judgeModelEdit.text.toString().trim()
            if (key.isBlank()) { judgeResult.text = "請先填金鑰"; return@cardBtn }
            judgeResult.text = "測試中…"
            // Provider follows the address when it is still a known preset host,
            // so a stale pill selection cannot send a TypeSafe path to OpenRouter.
            val provider = resolveJudgeProvider(judgeProviderIdx, base)
            if (provider == Prefs.PROVIDER_CUSTOM && base.isBlank()) {
                judgeResult.text = "自定義檔要填完整 URL（帶路徑）"; return@cardBtn
            }
            // Custom means we know nothing about the endpoint — guessing a model
            // name here would test something the user never asked for.
            if (provider == Prefs.PROVIDER_CUSTOM && model.isBlank()) {
                judgeResult.text = "請填寫模型名"; return@cardBtn
            }
            val probe = draftPrefs(SCRATCH_JUDGE) {
                judgeProvider = provider
                judgeBaseUrl = base.ifBlank { defaultJudgeBase(provider) }
                judgeKey = key
                judgeModel = model.ifBlank { defaultJudgeModel(provider) }
            }
            worker.execute {
                val t0 = System.currentTimeMillis()
                val demo = ChatSnapshot("連通測試", listOf(
                    Msg("other", "在嗎？"), Msg("me", "在")))
                val a = JudgeClient(probe).judge(demo, prefs.relationship)
                val ms = System.currentTimeMillis() - t0
                main.post {
                    judgeResult.text = if (a.error != null) "失敗（${ms}ms）：${a.error}"
                    else "成功 ${ms}ms · 意圖=${a.trueIntent?.choice ?: "?"}" +
                        "（置信 ${pct(a.trueIntent?.confidence)}）"
                }
            }
        })
        judgeCard.addView(judgeResult)
        root.addView(judgeCard)

        // --- 回覆接口 ---
        val replyCard = card()
        replyCard.addView(cardTitle("回覆接口"))
        replyCard.addView(text("生成 3 條候選回覆。任何 OpenAI 相容地址，填到 /v1 為止。", 12f, sub))

        val replyBaseEdit = edit(prefs.replyBaseUrl, Prefs.DEFAULT_REPLY_BASE)
        val replyModelEdit = edit(prefs.replyModel, Prefs.DEFAULT_REPLY_MODEL)
        val replyIdx = when (prefs.replyBaseUrl.trim().trimEnd('/')) {
            Prefs.DEFAULT_REPLY_BASE -> 0
            Prefs.VERCEL_OPENAI_BASE -> 1
            else -> 2
        }
        replyCard.addView(pills(
            listOf("OpenRouter", "Vercel", "自定義"), replyIdx) { idx ->
            when (idx) {
                0 -> { replyBaseEdit.setText(Prefs.DEFAULT_REPLY_BASE); replyModelEdit.setText(Prefs.DEFAULT_REPLY_MODEL) }
                1 -> { replyBaseEdit.setText(Prefs.VERCEL_OPENAI_BASE); replyModelEdit.setText(Prefs.VERCEL_REPLY_MODEL) }
            }
        })
        replyCard.addView(label("Base URL"))
        replyCard.addView(replyBaseEdit)
        replyCard.addView(label("金鑰"))
        replyCard.addView(edit(prefs.replyKey, "留空則用判斷接口金鑰", password = true).also { replyKeyEdit = it })
        replyCard.addView(label("模型"))
        replyCard.addView(replyModelEdit)
        val replyResult = resultText()
        replyCard.addView(cardBtn("測試回覆") {
            val base = replyBaseEdit.text.toString().trim()
            val model = replyModelEdit.text.toString().trim()
            val probe = draftPrefs(SCRATCH_REPLY) {
                judgeKey = judgeKeyEdit.text.toString().trim()
                replyBaseUrl = base.ifBlank { Prefs.DEFAULT_REPLY_BASE }
                replyKey = replyKeyEdit.text.toString().trim()
                replyModel = model.ifBlank { Prefs.DEFAULT_REPLY_MODEL }
            }
            if (probe.effectiveReplyKey().isBlank()) { replyResult.text = "請先填金鑰（或填判斷接口金鑰）"; return@cardBtn }
            replyResult.text = "測試中…"
            worker.execute {
                val t0 = System.currentTimeMillis()
                var err: String? = null
                val out = try {
                    ReplyClient(probe).ping()
                } catch (e: Exception) { err = e.message; "" }
                val ms = System.currentTimeMillis() - t0
                main.post {
                    replyResult.text = if (err != null) "失敗（${ms}ms）：$err"
                    else "成功 ${ms}ms · 返回：${out.replace("\n", " ").take(60)}"
                }
            }
        })
        replyCard.addView(replyResult)
        root.addView(replyCard)

        // --- 視覺接口 ---
        val visionCard = card()
        visionCard.addView(cardTitle("視覺接口（OCR 用，可先不填）"))
        visionCard.addView(text("讀不到控制元件樹的 App 走截圖識別。B 階段才用到，現在填不填都不影響。", 12f, sub))

        val visionBaseEdit = edit(prefs.visionBaseUrl, Prefs.DEFAULT_VISION_BASE)
        val visionModelEdit = edit(prefs.visionModel, Prefs.DEFAULT_VISION_MODEL)
        val visionIdx = when (prefs.visionBaseUrl.trim().trimEnd('/')) {
            Prefs.DEFAULT_VISION_BASE -> 0
            Prefs.VERCEL_OPENAI_BASE -> 1
            else -> 2
        }
        visionCard.addView(pills(
            listOf("OpenRouter", "Vercel", "自定義"), visionIdx) { idx ->
            when (idx) {
                0 -> { visionBaseEdit.setText(Prefs.DEFAULT_VISION_BASE); visionModelEdit.setText(Prefs.DEFAULT_VISION_MODEL) }
                1 -> { visionBaseEdit.setText(Prefs.VERCEL_OPENAI_BASE); visionModelEdit.setText(Prefs.VERCEL_VISION_MODEL) }
            }
        })
        visionCard.addView(label("Base URL"))
        visionCard.addView(visionBaseEdit)
        visionCard.addView(label("金鑰"))
        visionCard.addView(edit(prefs.visionKey, "留空則用回覆接口金鑰", password = true).also { visionKeyEdit = it })
        visionCard.addView(label("模型"))
        visionCard.addView(visionModelEdit)
        val visionResult = resultText()
        visionCard.addView(cardBtn("測試視覺") {
            val visionBase = visionBaseEdit.text.toString().trim()
            val probe = draftPrefs(SCRATCH_VISION) {
                judgeKey = judgeKeyEdit.text.toString().trim()
                replyBaseUrl = replyBaseEdit.text.toString().trim().ifBlank { Prefs.DEFAULT_REPLY_BASE }
                replyKey = replyKeyEdit.text.toString().trim()
                visionBaseUrl = visionBase
                visionKey = visionKeyEdit.text.toString().trim()
                visionModel = visionModelEdit.text.toString().trim().ifBlank { Prefs.DEFAULT_VISION_MODEL }
            }
            if (probe.effectiveVisionKey().isBlank()) { visionResult.text = "請先填金鑰（或填回覆/判斷接口金鑰）"; return@cardBtn }
            visionResult.text = "測試中…"
            worker.execute {
                val t0 = System.currentTimeMillis()
                var err: String? = null
                val out = try {
                    VisionClient(probe).ask(whitePixelJpegB64(), "這張圖是什麼顏色？只回答顏色。")
                } catch (e: Exception) { err = e.message; "" }
                val ms = System.currentTimeMillis() - t0
                main.post {
                    visionResult.text = if (err != null) "失敗（${ms}ms）：$err"
                    else "成功 ${ms}ms · 返回：${out.replace("\n", " ").take(60)}"
                }
            }
        })
        visionCard.addView(visionResult)
        root.addView(visionCard)

        // =================== 分析 ===================
        root.addView(section("分析"))
        val card2 = card()
        card2.addView(label("關係描述（給 Jev 判斷用）"))
        val relEdit = edit(prefs.relationship, Prefs.DEFAULT_REL)
        card2.addView(relEdit)
        card2.addView(label("會話白名單（每行一個關鍵詞，空=所有會話）"))
        val wlEdit = edit(prefs.whitelist.joinToString("\n"), "留空則對所有會話生效").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE; minLines = 2
        }
        card2.addView(wlEdit)
        val autoRow = toggleRow("對方發訊息時自動分析", prefs.autoAnalyze)
        card2.addView(autoRow)
        card2.addView(text("關閉時（預設）只在懸浮窗顯示分析對象與「分析」按鈕，點了才送出，貼圖、照片或不需要回的訊息不花 token。", 11f, sub))

        // --- OCR 兜底（B 階段）---
        val ocrFallbackRow = toggleRow("樹讀不到正文時用 OCR 兜底", prefs.ocrFallback)
        card2.addView(ocrFallbackRow)
        card2.addView(text("正文是畫上去的 App，節點樹裡讀不到，這時截一次屏本地識別（不上傳）。", 11f, sub))
        val ocrAutoRow = toggleRow("OCR 模式自動分析", prefs.ocrAutoAnalyze)
        card2.addView(ocrAutoRow)
        card2.addView(text("關閉時 OCR 認完只亮懸浮球，點一下再分析。", 11f, sub))

        // --- 知識庫 / 關聯上下文（D 階段） ---
        val ctxRow = toggleRow("記錄聊天曆史（只存本機，用於關聯上下文）", prefs.contextEnabled)
        card2.addView(ctxRow)
        card2.addView(text("關閉時不寫任何聊天內容到磁碟；筆記與聯絡人匹配仍然照常工作。", 11f, sub))
        card2.addView(label("注入最近歷史條數（0–100）"))
        val ctxCountEdit = edit(prefs.contextHistoryCount.toString(), "30").apply {
            inputType = InputType.TYPE_CLASS_NUMBER
        }
        card2.addView(ctxCountEdit)
        card2.addView(cardBtn("知識庫與聯絡人") {
            startActivity(android.content.Intent(this, KnowledgeActivity::class.java))
        })
        val kbResult = resultText()
        card2.addView(cardBtn("清空知識庫與歷史") {
            val c = KbStore.get(this).counts()
            androidx.appcompat.app.AlertDialog.Builder(this)
                .setTitle("清空知識庫與歷史")
                .setMessage("將刪除 ${c.notes} 條筆記、${c.contacts} 個聯絡人、${c.logLines} 條聊天曆史。" +
                    "金鑰、白名單等設定不受影響。不可恢復。")
                .setPositiveButton("清空") { _, _ ->
                    KbStore.get(this).clearAll()
                    kbResult.text = "已清空知識庫與歷史"
                }
                .setNegativeButton("取消", null)
                .show()
        })
        // Deliberately low-key: a developer aid, not a user feature.
        card2.addView(text("自檢", 12f, sub).apply {
            setPadding(dp(2), dp(12), dp(8), dp(2))
            setOnClickListener {
                kbResult.text = "自檢中…"
                worker.execute {
                    val out = try { KbSelfCheck.run(this@SettingsActivity) }
                    catch (e: Exception) { "自檢異常：${e.javaClass.simpleName} ${e.message ?: ""}" }
                    main.post { kbResult.text = out }
                }
            }
        })
        card2.addView(kbResult)
        root.addView(card2)

        // =================== 外觀 ===================
        root.addView(section("外觀"))
        val card3 = card()
        val opacityLabel = label("懸浮窗不透明度：${prefs.overlayOpacity}%")
        card3.addView(opacityLabel)
        card3.addView(text("越低越透，越能看清下面的聊天", 12f, sub))
        val seek = SeekBar(this).apply {
            max = 40; progress = prefs.overlayOpacity - 60  // 60..100
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(sb: SeekBar?, p: Int, u: Boolean) {
                    opacityLabel.text = "懸浮窗不透明度：${p + 60}%"
                }
                override fun onStartTrackingTouch(sb: SeekBar?) {}
                override fun onStopTrackingTouch(sb: SeekBar?) {}
            })
        }
        card3.addView(seek)
        root.addView(card3)

        // =================== 關於與隱私 ===================
        root.addView(section("關於與隱私"))
        val aboutCard = card()
        aboutCard.addView(text(
            "這個 App 會讀取你當前聊天視窗的文字，發給你自己配置的模型接口做判斷和起草回覆。作者不運營伺服器，收不到你的資料。",
            12f, sub))
        // Upstream's MIT NOTICE asks every redistribution to credit the source on
        // its About page and to keep LICENSE + NOTICE (bundled under assets/legal).
        aboutCard.addView(text(
            "基於 Jev 聊天助手（${UPSTREAM_URL}）二次開發。MIT 授權，Copyright © 2026 Finderchangchang " +
                "與 jev-chat 貢獻者；本版本由 SanHsien 修改與維護，非原作者出品或背書。",
            12f, sub).apply { setPadding(0, dp(8), 0, 0) })
        aboutCard.addView(cardBtn("隱私政策") { openUrl(PRIVACY_URL) })
        aboutCard.addView(cardBtn("開源倉庫") { openUrl(REPO_URL) })
        aboutCard.addView(cardBtn("上游專案") { openUrl(UPSTREAM_URL) })
        aboutCard.addView(cardBtn("授權條款與聲明") { showLegal() })
        aboutCard.addView(text(versionLabel(), 11f, sub).apply { setPadding(0, dp(10), 0, dp(2)) })
        root.addView(aboutCard)

        // =================== 儲存 ===================
        root.addView(primaryBtn("儲存全部設定") {
            // Address wins over the pill: a preset HOST in the box means that
            // preset's provider (and so its path), whatever the pill last said.
            val judgeBaseTyped = judgeBaseEdit.text.toString().trim()
            val judgeProv = resolveJudgeProvider(judgeProviderIdx, judgeBaseTyped)
            val judgeModelTyped = judgeModelEdit.text.toString().trim()
            prefs.judgeProvider = judgeProv
            // Blank falls back to THIS provider's preset — never OpenRouter's by
            // default. Custom is left exactly as typed (blank included): guessing
            // a URL for it would silently point somewhere the user did not choose.
            prefs.judgeBaseUrl = when {
                judgeBaseTyped.isNotBlank() -> judgeBaseTyped
                judgeProv == Prefs.PROVIDER_CUSTOM -> ""
                else -> defaultJudgeBase(judgeProv)
            }
            prefs.judgeKey = judgeKeyEdit.text.toString()
            prefs.judgeModel = when {
                judgeModelTyped.isNotBlank() -> judgeModelTyped
                judgeProv == Prefs.PROVIDER_CUSTOM -> ""
                else -> defaultJudgeModel(judgeProv)
            }

            prefs.replyBaseUrl = replyBaseEdit.text.toString().trim().ifBlank { Prefs.DEFAULT_REPLY_BASE }
            prefs.replyKey = replyKeyEdit.text.toString()
            prefs.replyModel = replyModelEdit.text.toString().trim().ifBlank { Prefs.DEFAULT_REPLY_MODEL }

            prefs.visionBaseUrl = visionBaseEdit.text.toString().trim()
            prefs.visionKey = visionKeyEdit.text.toString()
            prefs.visionModel = visionModelEdit.text.toString().trim().ifBlank { Prefs.DEFAULT_VISION_MODEL }

            prefs.relationship = relEdit.text.toString()   // blank stays blank, on purpose
            prefs.whitelist = wlEdit.text.toString().split("\n")
                .map { it.trim() }.filter { it.isNotEmpty() }.toSet()
            prefs.autoAnalyze = (autoRow.tag as? Boolean) ?: false
            prefs.ocrFallback = (ocrFallbackRow.tag as? Boolean) ?: true
            prefs.ocrAutoAnalyze = (ocrAutoRow.tag as? Boolean) ?: false
            prefs.contextEnabled = (ctxRow.tag as? Boolean) ?: false
            prefs.contextHistoryCount =
                ctxCountEdit.text.toString().trim().toIntOrNull()?.coerceIn(0, 100) ?: 30
            prefs.overlayOpacity = seek.progress + 60
            Toast.makeText(this, "已儲存", Toast.LENGTH_SHORT).show()
        })

        setContentView(scroll)
    }

    // Held as fields because several test buttons read each other's key box.
    private lateinit var judgeKeyEdit: EditText
    private lateinit var replyKeyEdit: EditText
    private lateinit var visionKeyEdit: EditText

    private fun providerOf(idx: Int) = when (idx) {
        1 -> Prefs.PROVIDER_TYPESAFE
        2 -> Prefs.PROVIDER_VERCEL
        3 -> Prefs.PROVIDER_ZEN
        4 -> Prefs.PROVIDER_CUSTOM
        else -> Prefs.PROVIDER_OPENROUTER
    }

    /**
     * The provider actually implied by what is in the address box. A preset host
     * carries its own path (`/alpha/decisions`, `/v1/systemone`), so leaving that
     * host in the box while the pill says something else would POST the wrong
     * path — or, for custom, the bare API root.
     */
    private fun resolveJudgeProvider(idx: Int, base: String): String =
        when (base.trim().trimEnd('/')) {
            Prefs.DEFAULT_JUDGE_BASE_OPENROUTER -> Prefs.PROVIDER_OPENROUTER
            Prefs.DEFAULT_JUDGE_BASE_TYPESAFE -> Prefs.PROVIDER_TYPESAFE
            Prefs.DEFAULT_JUDGE_BASE_VERCEL -> Prefs.PROVIDER_VERCEL
            Prefs.DEFAULT_JUDGE_BASE_ZEN -> Prefs.PROVIDER_ZEN
            else -> providerOf(idx)
        }

    /** The full endpoint a preset host would have been expanded to. */
    private fun expandJudgeUrl(base: String): String = when (base.trim().trimEnd('/')) {
        Prefs.DEFAULT_JUDGE_BASE_OPENROUTER -> Prefs.DEFAULT_JUDGE_BASE_OPENROUTER + "/alpha/decisions"
        Prefs.DEFAULT_JUDGE_BASE_TYPESAFE -> Prefs.DEFAULT_JUDGE_BASE_TYPESAFE + "/v1/systemone"
        Prefs.DEFAULT_JUDGE_BASE_VERCEL -> Prefs.DEFAULT_JUDGE_BASE_VERCEL + "/v1/systemone"
        Prefs.DEFAULT_JUDGE_BASE_ZEN -> Prefs.DEFAULT_JUDGE_BASE_ZEN + "/v1/systemone"
        else -> base.trim()
    }

    private fun defaultJudgeBase(provider: String): String = when (provider) {
        Prefs.PROVIDER_TYPESAFE -> Prefs.DEFAULT_JUDGE_BASE_TYPESAFE
        Prefs.PROVIDER_VERCEL -> Prefs.DEFAULT_JUDGE_BASE_VERCEL
        Prefs.PROVIDER_ZEN -> Prefs.DEFAULT_JUDGE_BASE_ZEN
        else -> Prefs.DEFAULT_JUDGE_BASE_OPENROUTER
    }

    private fun defaultJudgeModel(provider: String): String = when (provider) {
        Prefs.PROVIDER_TYPESAFE -> Prefs.DEFAULT_JUDGE_MODEL_TYPESAFE
        Prefs.PROVIDER_VERCEL -> Prefs.DEFAULT_JUDGE_MODEL_VERCEL
        Prefs.PROVIDER_ZEN -> Prefs.DEFAULT_JUDGE_MODEL_ZEN
        else -> Prefs.DEFAULT_JUDGE_MODEL_OPENROUTER
    }

    /**
     * A throwaway [Prefs] view carrying exactly what is in the boxes right now,
     * so a test button probes the typed values rather than the saved ones. Each
     * button gets its OWN scratch file — they used to share one and clear it out
     * from under each other when two tests overlapped. The real config is never
     * touched either way.
     */
    private fun draftPrefs(scratchName: String, fill: Prefs.() -> Unit): Prefs {
        getSharedPreferences(scratchName, MODE_PRIVATE).edit().clear().commit()
        return Prefs(this, scratchName).apply(fill)
    }

    /** Opens an external link; swallows the failure with a toast rather than crashing. */
    /** LICENSE + NOTICE as shipped inside the APK (copied in at build time). */
    private fun showLegal() {
        val body = listOf("NOTICE", "LICENSE").joinToString("\n\n────────\n\n") { name ->
            runCatching { assets.open("legal/$name").bufferedReader(Charsets.UTF_8).use { it.readText() } }
                .getOrDefault("（找不到 ${name}）").trim()
        }
        val pad = dp(20)
        val content = ScrollView(this).apply {
            addView(text(body, 12f, ink).apply { setPadding(pad, pad, pad, pad); setTextIsSelectable(true) })
        }
        AlertDialog.Builder(this)
            .setTitle("授權條款與聲明")
            .setView(content)
            .setPositiveButton("關閉", null)
            .show()
    }

    private fun openUrl(url: String) {
        runCatching {
            startActivity(
                android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(url))
                    .addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        }.onFailure {
            Toast.makeText(this, "打不開瀏覽器", Toast.LENGTH_SHORT).show()
        }
    }

    private fun versionLabel(): String = try {
        val pi = packageManager.getPackageInfo(packageName, 0)
        "版本 v${pi.versionName}（${pi.longVersionCode}）"
    } catch (e: Exception) {
        "版本 —"
    }

    /** 1x1 white JPEG for the vision smoke test, via the real encoder path. */
    private fun whitePixelJpegB64(): String {
        val bmp = Bitmap.createBitmap(1, 1, Bitmap.Config.ARGB_8888)
        bmp.eraseColor(Color.WHITE)
        return VisionClient.encodeJpeg(bmp)
    }

    private fun pct(d: Double?): String =
        if (d == null) "?" else "${(d * 100).roundToInt()}%"

    /** Horizontal selectable pills; calls [onPick] with the chosen index. */
    private fun pills(options: List<String>, initial: Int, onPick: (Int) -> Unit): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        val views = ArrayList<TextView>()
        options.forEachIndexed { i, opt ->
            val pill = TextView(this).apply {
                text = opt; textSize = 12.5f; gravity = Gravity.CENTER
                setPadding(dp(13), dp(7), dp(13), dp(7))
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT).apply { rightMargin = dp(7) }
            }
            views.add(pill)
            pill.setOnClickListener {
                views.forEachIndexed { j, v -> paintPill(v, j == i) }
                onPick(i)
            }
            row.addView(pill)
        }
        views.forEachIndexed { j, v -> paintPill(v, j == initial) }
        val scroller = HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            addView(row)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(10) }
        }
        return scroller
    }

    private fun paintPill(v: TextView, on: Boolean) {
        v.setTextColor(if (on) Color.WHITE else sub)
        v.setTypeface(v.typeface, if (on) Typeface.BOLD else Typeface.NORMAL)
        v.background = round(dp(9), if (on) accent else pillOff)
    }

    private fun toggleRow(labelText: String, initial: Boolean): LinearLayout {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(12), 0, dp(2)); tag = initial
        }
        val lab = text(labelText, 14f, ink).apply {
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        val sw = TextView(this).apply {
            text = if (initial) "開" else "關"; textSize = 13f; gravity = Gravity.CENTER
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(if (initial) Color.WHITE else sub)
            background = round(dp(10), if (initial) accent else Color.parseColor("#E5E7EB"))
            setPadding(dp(18), dp(6), dp(18), dp(6))
        }
        sw.setOnClickListener {
            val now = !((row.tag as? Boolean) ?: true); row.tag = now
            sw.text = if (now) "開" else "關"
            sw.setTextColor(if (now) Color.WHITE else sub)
            sw.background = round(dp(10), if (now) accent else Color.parseColor("#E5E7EB"))
        }
        row.addView(lab); row.addView(sw)
        return row
    }

    // atoms
    private fun header(t: String) = text(t, 24f, ink, bold = true).apply { setPadding(0, 0, 0, dp(4)) }
    private fun section(t: String) = text(t, 12f, sub, bold = true).apply { setPadding(dp(2), dp(16), 0, dp(6)) }
    private fun label(t: String) = text(t, 13f, ink, bold = true).apply { setPadding(0, dp(12), 0, dp(4)) }
    private fun cardTitle(t: String) = text(t, 16f, ink, bold = true).apply { setPadding(0, dp(10), 0, dp(4)) }
    private fun resultText() = text("", 12.5f, sub).apply { setPadding(0, dp(10), 0, dp(2)) }

    private fun card() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        background = round(dp(14), Color.WHITE)
        setPadding(dp(14), dp(4), dp(14), dp(14))
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            .apply { topMargin = dp(10) }
    }

    private fun edit(value: String, hint: String, password: Boolean = false) = EditText(this).apply {
        setText(value); this.hint = hint; textSize = 14f; setTextColor(ink)
        setHintTextColor(Color.parseColor("#9CA3AF"))
        background = round(dp(8), Color.parseColor("#F3F4F6"))
        setPadding(dp(10), dp(10), dp(10), dp(10))
        // Masked, not VISIBLE_PASSWORD: an API key should not sit in plain sight.
        if (password) inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(2) }
    }

    private fun text(t: String, size: Float, color: Int, bold: Boolean = false) = TextView(this).apply {
        text = t; textSize = size; setTextColor(color); if (bold) setTypeface(typeface, Typeface.BOLD)
    }

    private fun primaryBtn(label: String, onClick: () -> Unit) = TextView(this).apply {
        text = label; textSize = 15f; gravity = Gravity.CENTER; setTypeface(typeface, Typeface.BOLD)
        setTextColor(Color.WHITE); background = round(dp(12), accent)
        setPadding(dp(16), dp(13), dp(16), dp(13))
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(18) }
        setOnClickListener { onClick() }
    }

    /** Outlined button sized for inside a card. */
    private fun cardBtn(label: String, onClick: () -> Unit) = TextView(this).apply {
        text = label; textSize = 14f; gravity = Gravity.CENTER; setTypeface(typeface, Typeface.BOLD)
        setTextColor(accent); background = round(dp(10), Color.WHITE, stroke = true)
        setPadding(dp(14), dp(10), dp(14), dp(10))
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(14) }
        setOnClickListener { onClick() }
    }

    private fun round(radius: Int, color: Int, stroke: Boolean = false) = GradientDrawable().apply {
        cornerRadius = radius.toFloat(); setColor(color); if (stroke) setStroke(dp(1), accent)
    }

    override fun onDestroy() { super.onDestroy(); worker.shutdownNow() }

    companion object {
        private const val TAG = "JEVASSIST"

        /** One scratch prefs file per test button; never the real config. */
        private const val SCRATCH_JUDGE = "jev_probe_scratch_judge"
        private const val SCRATCH_REPLY = "jev_probe_scratch_reply"
        private const val SCRATCH_VISION = "jev_probe_scratch_vision"

        private const val PRIVACY_URL = "https://github.com/SanHsien/jev-chat-jarvis/blob/main/PRIVACY.md"
        private const val REPO_URL = "https://github.com/SanHsien/jev-chat-jarvis"
        private const val UPSTREAM_URL = "https://github.com/jev-chat/jev-chat-jarvis"
    }
}
