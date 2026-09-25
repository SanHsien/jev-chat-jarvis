package com.jev.probe

import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.InputType
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.jev.probe.core.kb.Contact
import com.jev.probe.core.kb.KbStore
import com.jev.probe.core.kb.Note
import kotlin.math.roundToInt

/**
 * Knowledge base manager: the notes the assistant may quote, and the contacts
 * that tie a conversation title (across apps) to a person.
 *
 * Everything shown here lives in the app-private `filesDir/kb` directory and
 * nowhere else. Plain code-built views, same card/pill vocabulary as
 * [SettingsActivity].
 */
class KnowledgeActivity : AppCompatActivity() {

    private lateinit var store: KbStore
    private lateinit var container: LinearLayout

    /** 0 = notes, 1 = contacts. */
    private var tab = 0

    private val accent = Color.parseColor("#3A7AFE")
    private val ink = Color.parseColor("#111827")
    private val sub = Color.parseColor("#6B7280")
    private val pillOff = Color.parseColor("#EEF1F5")
    private val red = Color.parseColor("#DC2626")

    private fun dp(v: Int) = TypedValue.applyDimension(
        TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics).roundToInt()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = KbStore.get(this)
        window.decorView.setBackgroundColor(Color.parseColor("#F2F3F5"))

        val scroll = ScrollView(this)
        container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(28))
        }
        container.padForSystemBars()   // edge-to-edge: keep the title off the status bar
        scroll.addView(container)
        setContentView(scroll)
        render()
    }

    // --------------------------------------------------------------- screens

    private fun render() {
        container.removeAllViews()
        container.addView(text("知識庫與聯絡人", 24f, ink, bold = true))
        container.addView(text("只存在本機，不上傳。分析時按會話標題匹配聯絡人、按關鍵詞命中筆記。",
            12f, sub).apply { setPadding(0, dp(6), 0, dp(4)) })
        container.addView(tabs())
        if (tab == 0) renderNotes() else renderContacts()
    }

    private fun tabs(): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(12) }
        }
        listOf("筆記", "聯絡人").forEachIndexed { i, name ->
            val pill = TextView(this).apply {
                text = name; textSize = 13f; gravity = Gravity.CENTER
                setPadding(dp(18), dp(8), dp(18), dp(8))
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT).apply { rightMargin = dp(8) }
                setTextColor(if (i == tab) Color.WHITE else sub)
                setTypeface(typeface, if (i == tab) Typeface.BOLD else Typeface.NORMAL)
                background = round(dp(9), if (i == tab) accent else pillOff)
                setOnClickListener { tab = i; render() }
            }
            row.addView(pill)
        }
        return row
    }

    // ----------------------------------------------------------------- notes

    private fun renderNotes() {
        val notes = store.notes().sortedByDescending { it.updatedAt }
        container.addView(twoButtons("新建筆記", { editNoteDialog(null) },
            "從文字匯入", { importNotesDialog() }))
        if (notes.isEmpty()) {
            container.addView(emptyCard("還沒有筆記。寫點該記住的事實：習慣、忌口、專案代號、約定過的時間。"))
            return
        }
        notes.forEach { container.addView(noteRow(it)) }
        container.addView(text("點條目編輯，長按刪除。命中規則：任一標籤或標題出現在會話標題或最近 6 條訊息裡。",
            11f, sub).apply { setPadding(dp(2), dp(12), 0, 0) })
    }

    private fun noteRow(n: Note): View {
        val c = card()
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
        }
        val left = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        val head = n.title.ifBlank { "（無標題）" } + if (n.alwaysOn) "  · 常駐" else ""
        left.addView(text(head, 15f, ink, bold = true))
        left.addView(text(
            if (n.tags.isEmpty()) "無標籤" else "標籤：" + n.tags.joinToString("、"),
            12f, sub).apply { setPadding(0, dp(3), 0, 0) })
        left.addView(text(n.content.replace("\n", " ").take(46), 12f, sub)
            .apply { setPadding(0, dp(3), 0, 0) })
        row.addView(left)
        row.addView(smallToggle(n.enabled) {
            store.saveNote(n.copy(enabled = !n.enabled)); render()
        })
        c.addView(row)
        c.setOnClickListener { editNoteDialog(n) }
        c.setOnLongClickListener {
            confirm("刪除筆記", "刪除「${n.title}」？不可恢復。") {
                store.deleteNote(n.id); render()
            }
            true
        }
        return c
    }

    private fun editNoteDialog(existing: Note?) {
        val box = dialogBox()
        val titleEdit = edit(existing?.title ?: "", "標題，例如：口味忌口")
        val contentEdit = edit(existing?.content ?: "", "正文，寫清楚事實本身").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            minLines = 4; gravity = Gravity.TOP
        }
        val tagsEdit = edit(existing?.tags?.joinToString("，") ?: "", "逗號分隔，例如：吃飯，週末")
        val alwaysRow = toggleRow("常駐（每次分析都帶上）", existing?.alwaysOn ?: false)
        val enabledRow = toggleRow("啟用", existing?.enabled ?: true)
        box.addView(label("標題")); box.addView(titleEdit)
        box.addView(label("正文")); box.addView(contentEdit)
        box.addView(label("標籤")); box.addView(tagsEdit)
        box.addView(alwaysRow); box.addView(enabledRow)

        AlertDialog.Builder(this)
            .setTitle(if (existing == null) "新建筆記" else "編輯筆記")
            .setView(wrapScroll(box))
            .setPositiveButton("儲存") { _, _ ->
                val title = titleEdit.text.toString().trim()
                val content = contentEdit.text.toString().trim()
                if (title.isBlank() && content.isBlank()) {
                    toast("標題和正文不能都空著"); return@setPositiveButton
                }
                store.saveNote(Note(
                    id = existing?.id ?: KbStore.newId(),
                    title = title,
                    content = content,
                    tags = splitTags(tagsEdit.text.toString()),
                    alwaysOn = (alwaysRow.tag as? Boolean) ?: false,
                    enabled = (enabledRow.tag as? Boolean) ?: true
                ))
                render()
            }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun importNotesDialog() {
        val box = dialogBox()
        box.addView(text("按空行分段，每段第一行當標題，其餘當正文。", 12f, sub))
        val input = edit("", "口味忌口\n不吃香菜，海鮮過敏\n\n專案代號\n內部叫小藍").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            minLines = 8; gravity = Gravity.TOP
        }
        box.addView(input)
        AlertDialog.Builder(this)
            .setTitle("從文字匯入")
            .setView(wrapScroll(box))
            .setPositiveButton("匯入") { _, _ ->
                val chunks = input.text.toString().split(Regex("\\r?\\n[ \\t]*\\r?\\n"))
                var n = 0
                chunks.forEach { chunk ->
                    val lines = chunk.trim().split("\n").map { it.trim() }.filter { it.isNotEmpty() }
                    if (lines.isNotEmpty()) {
                        store.saveNote(Note(
                            id = KbStore.newId(),
                            title = lines.first(),
                            content = lines.drop(1).joinToString("\n")
                        ))
                        n++
                    }
                }
                toast(if (n == 0) "沒解析出內容" else "已匯入 $n 條")
                render()
            }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun splitTags(raw: String): List<String> =
        raw.split(",", "，", "、").map { it.trim() }.filter { it.isNotEmpty() }

    // -------------------------------------------------------------- contacts

    private fun renderContacts() {
        val contacts = store.contacts().sortedByDescending { it.updatedAt }
        container.addView(twoButtons("新建聯絡人", { editContactDialog(null) }, null, null))
        if (contacts.isEmpty()) {
            container.addView(emptyCard(
                "還沒有聯絡人。也可以在聊天里長按懸浮球，選「把當前會話存為聯絡人」。"))
            return
        }
        contacts.forEach { container.addView(contactRow(it)) }
        container.addView(text("點條目編輯，長按刪除。會話標題等於名字或任一別名即算命中（忽略大小寫與群人數字尾）。",
            11f, sub).apply { setPadding(dp(2), dp(12), 0, 0) })
    }

    private fun contactRow(c0: Contact): View {
        val c = card()
        c.addView(text(c0.name.ifBlank { "（無名）" }, 15f, ink, bold = true))
        if (c0.aliases.isNotEmpty())
            c.addView(text("別名：" + c0.aliases.joinToString("、"), 12f, sub)
                .apply { setPadding(0, dp(3), 0, 0) })
        if (c0.apps.isNotEmpty())
            c.addView(text("來源：" + c0.apps.joinToString("、") { appLabel(it) }, 12f, sub)
                .apply { setPadding(0, dp(3), 0, 0) })
        if (c0.relationship.isNotBlank())
            c.addView(text("關係：" + c0.relationship.replace("\n", " ").take(40), 12f, sub)
                .apply { setPadding(0, dp(3), 0, 0) })
        if (c0.notes.isNotBlank())
            c.addView(text("備註：" + c0.notes.replace("\n", " ").take(40), 12f, sub)
                .apply { setPadding(0, dp(3), 0, 0) })

        val logN = store.logSize(c0.id)
        val clear = TextView(this).apply {
            text = "清空此人歷史（$logN 條）"
            textSize = 12.5f; setTextColor(red); setTypeface(typeface, Typeface.BOLD)
            setPadding(0, dp(10), 0, dp(2))
            setOnClickListener {
                if (logN == 0) { toast("本來就沒有歷史"); return@setOnClickListener }
                confirm("清空歷史", "刪掉「${c0.name}」的 $logN 條聊天曆史？聯絡人檔案保留。") {
                    store.clearLog(c0.id); render()
                }
            }
        }
        c.addView(clear)
        c.setOnClickListener { editContactDialog(c0) }
        c.setOnLongClickListener {
            confirm("刪除聯絡人", "刪除「${c0.name}」及其全部歷史？不可恢復。") {
                store.deleteContact(c0.id); render()
            }
            true
        }
        return c
    }

    private fun editContactDialog(existing: Contact?) {
        val box = dialogBox()
        val nameEdit = edit(existing?.name ?: "", "名字，一般就是會話標題")
        val aliasEdit = edit(existing?.aliases?.joinToString("\n") ?: "", "每行一個，例如另一個 App 裡的暱稱").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            minLines = 3; gravity = Gravity.TOP
        }
        val relEdit = edit(existing?.relationship ?: "", "例如：同事，帶我做專案的組長")
        val notesEdit = edit(existing?.notes ?: "", "關於這個人要記住的事").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            minLines = 3; gravity = Gravity.TOP
        }
        box.addView(label("名字")); box.addView(nameEdit)
        box.addView(label("別名（每行一個）")); box.addView(aliasEdit)
        box.addView(label("關係")); box.addView(relEdit)
        box.addView(label("備註")); box.addView(notesEdit)

        AlertDialog.Builder(this)
            .setTitle(if (existing == null) "新建聯絡人" else "編輯聯絡人")
            .setView(wrapScroll(box))
            .setPositiveButton("儲存") { _, _ ->
                val name = nameEdit.text.toString().trim()
                if (name.isBlank()) { toast("名字不能空"); return@setPositiveButton }
                store.saveContact(Contact(
                    id = existing?.id ?: KbStore.newId(),
                    name = name,
                    aliases = aliasEdit.text.toString().split("\n")
                        .map { it.trim() }.filter { it.isNotEmpty() },
                    apps = existing?.apps ?: emptyList(),
                    relationship = relEdit.text.toString().trim(),
                    notes = notesEdit.text.toString().trim(),
                    autoSummary = existing?.autoSummary ?: ""
                ))
                render()
            }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun appLabel(pkg: String): String = when (pkg) {
        "jp.naver.line.android" -> "LINE"
        "com.twitter.android" -> "X"
        else -> pkg
    }

    // ----------------------------------------------------------------- atoms

    private fun confirm(title: String, msg: String, onYes: () -> Unit) {
        AlertDialog.Builder(this)
            .setTitle(title).setMessage(msg)
            .setPositiveButton("確定") { _, _ -> onYes() }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun toast(m: String) = Toast.makeText(this, m, Toast.LENGTH_SHORT).show()

    private fun dialogBox() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(20), dp(8), dp(20), dp(4))
    }

    private fun wrapScroll(v: View) = ScrollView(this).apply { addView(v) }

    private fun twoButtons(
        a: String, onA: () -> Unit,
        b: String?, onB: (() -> Unit)?
    ): View {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(12) }
        }
        row.addView(wideBtn(a, true, onA))
        if (b != null && onB != null) row.addView(wideBtn(b, false, onB))
        return row
    }

    private fun wideBtn(labelText: String, primary: Boolean, onClick: () -> Unit) = TextView(this).apply {
        text = labelText; textSize = 14f; gravity = Gravity.CENTER
        setTypeface(typeface, Typeface.BOLD)
        setTextColor(if (primary) Color.WHITE else accent)
        background = round(dp(11), if (primary) accent else Color.WHITE, stroke = !primary)
        setPadding(dp(12), dp(11), dp(12), dp(11))
        layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
            .apply { rightMargin = dp(8) }
        setOnClickListener { onClick() }
    }

    private fun smallToggle(on: Boolean, onClick: () -> Unit) = TextView(this).apply {
        text = if (on) "開" else "關"; textSize = 13f; gravity = Gravity.CENTER
        setTypeface(typeface, Typeface.BOLD)
        setTextColor(if (on) Color.WHITE else sub)
        background = round(dp(10), if (on) accent else Color.parseColor("#E5E7EB"))
        setPadding(dp(16), dp(6), dp(16), dp(6))
        setOnClickListener { onClick() }
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

    private fun emptyCard(msg: String): View = card().apply { addView(text(msg, 13f, sub)) }

    private fun card() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        background = round(dp(14), Color.WHITE)
        setPadding(dp(14), dp(12), dp(14), dp(12))
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            .apply { topMargin = dp(10) }
    }

    private fun label(t: String) = text(t, 13f, ink, bold = true).apply { setPadding(0, dp(12), 0, dp(4)) }

    private fun edit(value: String, hintText: String) = EditText(this).apply {
        setText(value); hint = hintText; textSize = 14f; setTextColor(ink)
        setHintTextColor(Color.parseColor("#9CA3AF"))
        background = round(dp(8), Color.parseColor("#F3F4F6"))
        setPadding(dp(10), dp(10), dp(10), dp(10))
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            .apply { topMargin = dp(2) }
    }

    private fun text(t: String, size: Float, color: Int, bold: Boolean = false) = TextView(this).apply {
        text = t; textSize = size; setTextColor(color)
        if (bold) setTypeface(typeface, Typeface.BOLD)
    }

    private fun round(radius: Int, color: Int, stroke: Boolean = false) = GradientDrawable().apply {
        cornerRadius = radius.toFloat(); setColor(color)
        if (stroke) setStroke(dp(1), accent)
    }
}
