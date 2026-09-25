package com.jev.probe.core.kb

import android.content.Context
import com.jev.probe.core.ChatSnapshot
import com.jev.probe.core.Msg
import com.jev.probe.core.Prefs

/**
 * On-device smoke test for the knowledge-base path, reachable from the settings
 * screen ("自檢"). It exercises the parts that are easy to get quietly wrong —
 * name normalization across half/full-width member counts, note keyword hits,
 * and history de-duplication against what is already on screen — then removes
 * everything it created.
 *
 * It runs against the real [KbStore] (temporary note + contact, deleted at the
 * end) but a scratch [Prefs] file, so the user's own contextEnabled setting is
 * never touched.
 */
object KbSelfCheck {

    private const val SCRATCH_PREFS = "jev_kb_selfcheck_scratch"
    private const val BARE = "測試群"
    private const val TITLE = "測試群(12)"
    private const val ALIAS = "測試群（12）"          // full-width parens on purpose
    private const val PADDED = "  測試群  "
    private const val OLD_LINE = "上週說好週五交自檢稿"

    /** @return a one-line human-readable pass/fail summary. */
    fun run(context: Context): String {
        val failures = ArrayList<String>()

        // 0. Name normalization, checked first and on its own: its patterns are
        //    compiled in KbStore's class initializer, and a pattern the device's
        //    regex engine rejects used to take the whole class (and every
        //    analysis) down with an ExceptionInInitializerError.
        runCatching {
            listOf(TITLE, ALIAS, PADDED, BARE).forEach { raw ->
                val got = KbStore.normalizeName(raw)
                if (got != BARE)
                    failures.add("名稱歸一化失敗：輸入 ${raw} 得到 ${got}，應為 ${BARE}")
            }
        }.onFailure {
            failures.add("名稱歸一化異常：${it.javaClass.simpleName} ${it.message ?: ""}")
        }

        val store = KbStore.get(context)
        val noteId = KbStore.newId()
        val contactId = KbStore.newId()
        val prefs = scratchPrefs(context)
        try {
            prefs.contextEnabled = true
            prefs.contextHistoryCount = 30

            store.saveNote(Note(
                id = noteId,
                title = "自檢臨時筆記",
                content = "自檢用的虛構事實：專案代號叫小藍。",
                tags = listOf("測試"),
                alwaysOn = false,
                enabled = true
            ))
            store.saveContact(Contact(
                id = contactId,
                name = "自檢臨時聯絡人",
                aliases = listOf(ALIAS),
                apps = listOf("com.jev.probe"),
                relationship = "自檢用的關係描述"
            ))

            val snapshot = ChatSnapshot(TITLE, listOf(
                Msg("other", "自檢訊息一：這條夠長可以去重"),
                Msg("me", "自檢訊息二：這條也夠長")
            ))

            // 1. contact hit via full-width alias + member-count stripping
            val ctx1 = ContextBuilder.build(context, snapshot, "com.jev.probe", prefs)
            if (ctx1.contact?.id != contactId)
                failures.add("聯絡人未命中（標題 ${TITLE} 應匹配別名 ${ALIAS}）")

            // 2. note hit via tag "測試" appearing in the conversation title
            if (ctx1.notes.none { it.id == noteId })
                failures.add("筆記未命中（tag=測試 應命中標題 ${TITLE}）")

            // 3. the on-screen messages were recorded but not echoed back as history
            if (ctx1.history.isNotEmpty())
                failures.add("歷史去重失敗：當屏訊息不該出現在注入歷史裡（${ctx1.history.size} 條）")
            if (store.logSize(contactId) != snapshot.messages.size)
                failures.add("歷史落盤條數不對：期望 ${snapshot.messages.size}，實際 ${store.logSize(contactId)}")

            // 4. an older line survives, and re-reading the same screen adds nothing
            //    (screenBatch=false: this is a hand-injected line, not a capture,
            //    so it is not measured against the last screen we recorded)
            store.appendLog(contactId, listOf(
                LogEntry("other", OLD_LINE, System.currentTimeMillis() - 86_400_000L, "com.jev.probe")),
                screenBatch = false)
            val ctx2 = ContextBuilder.build(context, snapshot, "com.jev.probe", prefs)
            if (ctx2.history.size != 1 || ctx2.history.firstOrNull()?.text != OLD_LINE)
                failures.add("歷史注入不對：期望僅 1 條舊訊息，實際 ${ctx2.history.size} 條")
            if (store.logSize(contactId) != snapshot.messages.size + 1)
                failures.add("重複採集被寫了第二遍：${store.logSize(contactId)} 條")

            // 5. background carries the fabricated fact into the prompt
            val background = ctx2.background("預設關係")
            if (!background.contains("小藍")) failures.add("background 裡沒有筆記正文")
            if (!background.contains("自檢用的關係描述")) failures.add("background 裡沒有聯絡人關係")

            // 6. history is off by default (opt-in only)
            prefs.contextEnabled = false
            if (ContextBuilder.build(context, snapshot, "com.jev.probe", prefs).history.isNotEmpty())
                failures.add("contextEnabled=false 時仍注入了歷史")
        } catch (e: Exception) {
            failures.add("異常：${e.javaClass.simpleName} ${e.message ?: ""}")
        } finally {
            runCatching { store.deleteNote(noteId) }
            runCatching { store.deleteContact(contactId) }
            runCatching {
                context.getSharedPreferences(SCRATCH_PREFS, Context.MODE_PRIVATE)
                    .edit().clear().commit()
            }
        }
        val counts = store.counts()
        return if (failures.isEmpty())
            "自檢透過：聯絡人匹配 / 筆記命中 / 歷史去重 / 預算注入都正常。" +
                "當前知識庫 ${counts.notes} 條筆記、${counts.contacts} 個聯絡人、${counts.logLines} 條歷史。"
        else "自檢失敗（${failures.size}）：" + failures.joinToString("；")
    }

    /** A [Prefs] bound to a throwaway SharedPreferences file (no migration, no log). */
    private fun scratchPrefs(context: Context): Prefs {
        context.getSharedPreferences(SCRATCH_PREFS, Context.MODE_PRIVATE).edit().clear().commit()
        return Prefs(context, SCRATCH_PREFS)
    }
}
