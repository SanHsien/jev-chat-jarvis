package com.jev.probe

import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.jev.probe.core.CaptureHealth
import com.jev.probe.core.Prefs
import kotlin.math.roundToInt

/**
 * Home / setup screen. Card-based layout with a live readiness summary, a
 * guided permission checklist (each row reflects its real granted state), a
 * prominent on/off switch, and a link to settings.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var prefs: Prefs
    private lateinit var container: LinearLayout
    // unflattenFromString expands a ROM's short form (".capture.ChatCaptureService")
    // to the full class name, so both stored forms compare equal.
    private val a11yComponent get() =
        "$packageName/com.jev.probe.capture.ChatCaptureService"
    private val healthHandler = Handler(Looper.getMainLooper())
    private var lastHealth = ""
    private val refreshHealth = object : Runnable {
        override fun run() {
            val health = "${CaptureHealth.state(isA11yEnabled())}:${CaptureHealth.keepAliveFailure}"
            if (health != lastHealth) { lastHealth = health; build() }
            healthHandler.postDelayed(this, 1000)
        }
    }

    private val accent = Color.parseColor("#3A7AFE")
    private val green = Color.parseColor("#16A34A")
    private val red = Color.parseColor("#DC2626")
    private val ink = Color.parseColor("#111827")
    private val sub = Color.parseColor("#6B7280")

    private fun dp(v: Int) = TypedValue.applyDimension(
        TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics).roundToInt()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        window.decorView.setBackgroundColor(Color.parseColor("#F2F3F5"))

        val scroll = ScrollView(this)
        container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(28))
        }
        container.padForSystemBars()   // edge-to-edge: keep the title off the status bar
        scroll.addView(container)
        setContentView(scroll)
    }

    override fun onResume() {
        super.onResume()
        build()
        healthHandler.post(refreshHealth)
    }

    override fun onPause() {
        healthHandler.removeCallbacks(refreshHealth)
        super.onPause()
    }

    private fun build() {
        container.removeAllViews()

        container.addView(text("對話副駕", 24f, ink, bold = true))
        container.addView(text("在聊天 App 旁讀對方訊息（已支援 LINE、X），給出判斷和候選回覆。傳送始終由你手動點。",
            13f, sub).apply { setPadding(0, dp(6), 0, dp(16)) })

        val a11y = isA11yEnabled()
        val overlay = Settings.canDrawOverlays(this)
        val key = prefs.hasKey()   // judge route key: the one analysis cannot run without
        val ready = CaptureHealth.state(a11y) == CaptureHealth.State.CONNECTED && overlay && key && prefs.enabled

        // Readiness card
        container.addView(statusCard(ready, a11y, overlay, key))
        container.addView(privacyHint())

        // Permission checklist
        container.addView(sectionLabel("權限設定"))
        val connected = CaptureHealth.state(a11y) == CaptureHealth.State.CONNECTED
        container.addView(actionRow(
            if (!a11y) "開啟無障礙服務" else if (!connected) "恢復讀屏服務" else "無障礙服務設定",
            if (a11y && !connected) "已授權，但讀屏服務未連線。請關閉 Jev 無障礙開關再開啟，返回後自動檢查。"
            else "讀取當前聊天視窗的訊息文字"
        ) { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) })
        container.addView(permCard("懸浮窗權限", "在聊天視窗上方顯示分析卡片", overlay) {
            startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
        })
        // Android 13+: a sideloaded app's accessibility and overlay switches are
        // "restricted settings" — the system shows "應用程式存取權已遭拒絕" until the
        // user allows them from the app-info page. Code cannot lift this; guide the user.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && (!a11y || !overlay)) {
            container.addView(actionRow(
                "被系統拒絕？先允許受限制的設定",
                "非 Play 商店安裝的 App，Android 13 以後要先解除限制：點這裡開「應用程式資訊」→ 右上角 ⋮ →「允許受限制的設定」，" +
                    "驗證後再回來開無障礙與懸浮窗。看不到 ⋮ 的話，先去無障礙設定點一次 對話副駕，再回來。用 adb install 安裝則不受限制。"
            ) {
                runCatching {
                    startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
                }
            })
        }
        container.addView(permCard("自啟動 + 省電無限制", "vivo / 小米等機型請允許自啟動和背景執行，降低被系統清理的機率", null) {
            runCatching {
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
            }
        })

        // Actions
        container.addView(sectionLabel("其他"))
        container.addView(actionRow("設定", "金鑰 · 模型 · 關係 · 透明度 · 會話白名單") {
            startActivity(Intent(this, SettingsActivity::class.java))
        })

        // Master toggle
        val toggle = bigToggle(prefs.enabled)
        toggle.setOnClickListener {
            prefs.enabled = !prefs.enabled
            build()
        }
        container.addView(toggle)
    }

    // ---------------------------------------------------------------- cards

    private fun statusCard(ready: Boolean, a11y: Boolean, overlay: Boolean, key: Boolean): View {
        val c = cardBox()
        val head = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        head.addView(dot(if (ready) green else red).apply {
            (layoutParams as LinearLayout.LayoutParams).rightMargin = dp(10)
        })
        val headline = when {
            !prefs.enabled -> "助手已暫停"
            a11y && CaptureHealth.state(a11y) != CaptureHealth.State.CONNECTED -> "讀屏服務未連線"
            ready -> "已就緒，可以用了"
            else -> "尚未就緒"
        }
        head.addView(text(headline, 16f, if (ready) green else ink, bold = true))
        c.addView(head)
        val state = CaptureHealth.state(a11y)
        c.addView(checkLine("無障礙授權：", a11y, "已開啟", "未開啟"))
        c.addView(checkLine("讀屏服務：", state == CaptureHealth.State.CONNECTED, "已連線",
            if (a11y) "未連線，可能已停止或正在連線" else "等待授權"))
        if (!prefs.enabled) c.addView(text("助手已暫停，請使用下方開關開啟", 12f, sub))
        CaptureHealth.keepAliveFailure?.let {
            c.addView(text("背景保活啟動失敗（$it），請檢查自啟動和背景耗電限制。讀屏服務可能被系統清理。", 12f, red))
        }
        c.addView(checkLine("懸浮窗", overlay))
        c.addView(checkLine("金鑰", key, okWord = "已設", noWord = "未設"))
        // History recording is opt-in (off by default). Mention it here, never block on it.
        if (!prefs.contextEnabled) {
            c.addView(text("關聯上下文未開啟，可在設定裡開啟", 12f, sub).apply {
                setPadding(0, dp(8), 0, 0)
            })
        }
        return c
    }

    /** One tappable line under the readiness card, opening the privacy policy page. */
    private fun privacyHint(): View = text("讀取的聊天內容只發往你自己配置的接口 · 隱私政策", 11f, sub).apply {
        setPadding(dp(2), dp(8), 0, 0)
        setOnClickListener { openUrl(PRIVACY_URL) }
    }

    /** Opens an external link; swallows the failure with a toast rather than crashing. */
    private fun openUrl(url: String) {
        runCatching {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }.onFailure {
            Toast.makeText(this, "打不開瀏覽器", Toast.LENGTH_SHORT).show()
        }
    }

    private fun checkLine(label: String, ok: Boolean, okWord: String = "已開", noWord: String = "未開"): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(5), 0, 0)
        }
        row.addView(text(if (ok) "✓" else "✗", 14f, if (ok) green else red, bold = true).apply {
            (this as TextView).width = dp(22)
        })
        row.addView(text(label + (if (ok) okWord else noWord), 13f, sub))
        return row
    }

    private fun permCard(title: String, desc: String, granted: Boolean?, onClick: () -> Unit): View {
        val c = cardBox()
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        val left = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        left.addView(text(title, 15f, ink, bold = true))
        left.addView(text(desc, 12f, sub).apply { setPadding(0, dp(3), 0, 0) })
        if (granted == true) left.addView(text("✓ 已開啟", 12f, green, bold = true).apply { setPadding(0, dp(4), 0, 0) })
        row.addView(left)
        row.addView(btn(if (granted == true) "已開啟" else "去開啟", granted != true, onClick))
        c.addView(row)
        return c
    }

    private fun actionRow(title: String, desc: String, onClick: () -> Unit): View {
        val c = cardBox()
        c.setOnClickListener { onClick() }
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        val left = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        left.addView(text(title, 15f, ink, bold = true))
        left.addView(text(desc, 12f, sub).apply { setPadding(0, dp(3), 0, 0) })
        row.addView(left)
        row.addView(text("›", 22f, sub))
        c.addView(row)
        return c
    }

    private fun bigToggle(on: Boolean): View {
        return TextView(this).apply {
            text = if (on) "助手已開啟 · 點選關閉" else "助手已關閉 · 點選開啟"
            textSize = 15f; gravity = Gravity.CENTER; setTypeface(typeface, Typeface.BOLD)
            setTextColor(if (on) Color.WHITE else accent)
            background = roundBg(dp(14), if (on) accent else Color.WHITE, stroke = !on)
            setPadding(dp(16), dp(15), dp(16), dp(15))
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { topMargin = dp(18) }
        }
    }

    // ---------------------------------------------------------------- atoms

    private fun cardBox(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        background = roundBg(dp(14), Color.WHITE)
        setPadding(dp(14), dp(13), dp(14), dp(13))
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = dp(10) }
    }

    private fun sectionLabel(t: String) = text(t, 12f, sub, bold = true).apply {
        setPadding(dp(2), dp(18), 0, dp(2))
    }

    private fun text(t: String, size: Float, color: Int, bold: Boolean = false) = TextView(this).apply {
        text = t; textSize = size; setTextColor(color)
        if (bold) setTypeface(typeface, Typeface.BOLD)
    }

    private fun dot(color: Int) = View(this).apply {
        background = GradientDrawable().apply { shape = GradientDrawable.OVAL; setColor(color) }
        layoutParams = LinearLayout.LayoutParams(dp(10), dp(10))
    }

    private fun btn(label: String, enabled: Boolean, onClick: () -> Unit) = TextView(this).apply {
        text = label; textSize = 13f; gravity = Gravity.CENTER; setTypeface(typeface, Typeface.BOLD)
        setTextColor(if (enabled) Color.WHITE else sub)
        background = roundBg(dp(10), if (enabled) accent else Color.parseColor("#E5E7EB"))
        setPadding(dp(16), dp(8), dp(16), dp(8))
        if (enabled) setOnClickListener { onClick() }
    }

    private fun roundBg(radius: Int, color: Int, stroke: Boolean = false) = GradientDrawable().apply {
        cornerRadius = radius.toFloat(); setColor(color)
        if (stroke) setStroke(dp(1), accent)
    }

    private fun isA11yEnabled(): Boolean {
        val enabled = Settings.Secure.getString(contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES) ?: return false
        return enabled.split(':').any { android.content.ComponentName.unflattenFromString(it)?.flattenToString() == a11yComponent }
    }

    companion object {
        private const val PRIVACY_URL = "https://github.com/SanHsien/jev-chat-jarvis/blob/main/PRIVACY.md"
    }
}
