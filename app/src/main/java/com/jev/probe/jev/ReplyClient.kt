package com.jev.probe.jev

import com.jev.probe.core.ChatSnapshot
import com.jev.probe.core.focusSpeaker
import com.jev.probe.core.isGroupChat
import com.jev.probe.core.Prefs
import com.jev.probe.core.kb.ChatContext
import org.json.JSONArray
import org.json.JSONObject

/**
 * The generative route: any OpenAI-compatible `/chat/completions` endpoint.
 * Drafts the 3 candidate replies, and (D stage) summarizes text. Reads
 * replyBaseUrl / replyKey / replyModel from [Prefs].
 */
class ReplyClient(private val prefs: Prefs) {

    /**
     * Exactly 3 varied candidate replies in Chinese.
     *
     * @param ctx D-stage knowledge context. When present its background and
     *        history are prepended to the prompt with an instruction to stay
     *        consistent with them and invent nothing beyond them.
     */
    fun draft(snapshot: ChatSnapshot, relationship: String, ctx: ChatContext? = null): List<String> {
        // Group chats (fork): label each line with the speaker and name the addressee.
        val group = snapshot.isGroupChat()
        val convo = snapshot.messages.takeLast(10).joinToString("\n") {
            val who = when {
                it.side == "me" -> "我"
                group && it.speaker != null -> it.speaker
                else -> "對方"
            }
            who + "：" + it.text
        }
        val focus = snapshot.focusSpeaker()
        val addressee = if (group && focus != null)
            "這是群聊。回覆對象是「${focus}」（對方最新一條訊息的傳送者），其他人的發言只作背景。\n\n" else ""
        val sys = "你是中文即時通訊回覆助手，一律使用繁體中文（台灣用語）。只輸出一個 JSON 陣列，含且僅含 3 條候選回覆文字，" +
            "三條策略要有區別（例如：一條穩妥承接、一條給具體行動或承諾、一條簡短低姿態）。" +
            "每條不超過 40 字，口語、自然、像真人在聊天軟體裡發訊息。不要解釋，不要加引號以外的內容，直接輸出 JSON 陣列。"
        val user = knowledgeBlock(relationship, ctx) +
            "關係：${relationship}\n\n" + addressee + "最近對話：\n${convo}\n\n請給出 3 條候選回覆。"
        return parseThree(chat(sys, user, temperature = 0.8))
    }

    /** The background + history preamble; empty string when there is no context. */
    private fun knowledgeBlock(relationship: String, ctx: ChatContext?): String {
        ctx ?: return ""
        val background = ctx.background(relationship)
        val history = ctx.history
        if (background.isBlank() && history.isEmpty()) return ""
        val sb = StringBuilder()
        sb.append("以下是關於我和對方的背景與知識庫，回覆必須與之一致，")
            .append("可以直接引用其中事實，不要編造知識庫裡沒有的事實。\n")
        if (background.isNotBlank()) sb.append(background).append('\n')
        if (history.isNotEmpty()) {
            sb.append("\n更早的聊天記錄（越靠下越新）：\n")
            history.takeLast(prefs.contextHistoryCount.coerceIn(0, 100)).forEach {
                sb.append(if (it.side == "me") "我：" else "對方：").append(it.text).append('\n')
            }
        }
        sb.append('\n')
        return sb.toString()
    }

    /**
     * One plain chat round trip for the settings connectivity test. Deliberately
     * NOT [summarize]: the test should exercise the ordinary path, not whatever
     * the summary prompt happens to be.
     */
    fun ping(): String =
        chat("你是連通性測試助手，只按要求回答，不要解釋。", "請只回復兩個字：收到", temperature = 0.0).trim()

    /** Condense a block of text (used by the D-stage contact auto-summary). */
    fun summarize(text: String): String {
        if (text.isBlank()) return ""
        val sys = "你是中文摘要助手，一律使用繁體中文（台灣用語）。把給到的聊天記錄壓縮成不超過 120 字的第三人稱要點摘要，" +
            "只保留事實、偏好、承諾和待辦，不要評論，不要編造。直接輸出摘要正文。"
        return chat(sys, text, temperature = 0.2).trim()
    }

    /** One chat-completions round trip; returns the assistant message content. */
    private fun chat(system: String, user: String, temperature: Double): String {
        val url = prefs.replyEndpoint()
        val messages = JSONArray()
            .put(JSONObject().put("role", "system").put("content", system))
            .put(JSONObject().put("role", "user").put("content", user))
        val body = JSONObject()
            .put("model", prefs.replyModel)
            .put("messages", messages)
            .put("temperature", temperature)
        val resp = HttpJson.post(url, prefs.effectiveReplyKey(), body, Route.REPLY, HttpJson.headersFor(url))
        return resp.optJSONArray("choices")?.optJSONObject(0)
            ?.optJSONObject("message")?.optString("content") ?: ""
    }

    private fun parseThree(content: String): List<String> {
        val start = content.indexOf('[')
        val end = content.lastIndexOf(']')
        if (start >= 0 && end > start) {
            try {
                val arr = JSONArray(content.substring(start, end + 1))
                val out = ArrayList<String>()
                for (i in 0 until arr.length()) out.add(arr.getString(i).trim())
                if (out.size >= 3) return out.take(3)
                while (out.size < 3) out.add("（稍等，我看下）")
                return out
            } catch (_: Exception) { }
        }
        // Fallback: split lines.
        return ReplyLineParser.parse(content)
    }
}
