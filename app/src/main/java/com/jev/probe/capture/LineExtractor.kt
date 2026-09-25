package com.jev.probe.capture

import com.jev.probe.core.Msg

/**
 * The minimum of an accessibility node the LINE rules need. Kept free of Android
 * types so the rules run as a plain JVM unit test against a real `uiautomator dump`
 * (see LineExtractorTest); on device it wraps an AccessibilityNodeInfo.
 */
internal interface UiNode {
    val id: String?
    val text: String?
    val desc: String?
    val left: Int
    val right: Int
    val top: Int
    val children: List<UiNode>
}

/**
 * LINE (jp.naver.line.android) chat-room rules — original to this fork (SanHsien).
 * Verified against a dump of LINE's 1:1 chat room on 2026-09-25 (1440x3120,
 * Traditional Chinese UI):
 *
 * - Nodes are NOT obfuscated and message bodies carry real text: every message is
 *   one row `id/chat_ui_row_contentview_container`; its body is the TextView
 *   `id/chat_ui_message_text`. Photos are `id/chat_ui_row_image` and stickers
 *   `id/chat_ui_row_sticker_view` (no text) — kept as placeholders so the judgment
 *   knows something was sent.
 * - "In a chat room" = the compose box `id/chat_ui_message_edit` or the message list
 *   `id/chathistory_message_list` is in the tree. Neither → null (room list, LINE Pay,
 *   timeline…). The send button `id/chat_ui_send_button_image` is never touched.
 * - Side: my rows carry `id/chat_ui_linear_layout_meta_data` (read receipt + time,
 *   left of the bubble) and a "已讀" `id/chat_ui_row_read_count`; the other side's rows
 *   carry `id/chat_ui_row_layout_metadata` (time only, right of the bubble) and, on the
 *   first of a run, the avatar `id/chat_ui_row_thumbnail`. The avatar alone is not
 *   enough — a second consecutive message from the same person has none. Only when a
 *   row has none of these markers does geometry decide (my bubbles hug the right edge).
 * - Title: `id/header_title`.
 */
internal object LineExtractor {
    const val PKG = "jp.naver.line.android"
    private const val P = PKG + ":id/"

    const val ID_TITLE = P + "header_title"
    const val ID_INPUT = P + "chat_ui_message_edit"
    const val ID_LIST = P + "chathistory_message_list"
    const val ID_ROW = P + "chat_ui_row_contentview_container"
    const val ID_TEXT = P + "chat_ui_message_text"
    const val ID_IMAGE = P + "chat_ui_row_image"
    const val ID_STICKER = P + "chat_ui_row_sticker_view"
    private const val ID_MINE_META = P + "chat_ui_linear_layout_meta_data"
    private const val ID_READ = P + "chat_ui_row_read_count"
    private const val ID_OTHER_META = P + "chat_ui_row_layout_metadata"
    private const val ID_AVATAR = P + "chat_ui_row_thumbnail"

    const val PHOTO = "[照片]"
    const val STICKER = "[貼圖]"

    /** Result of reading one window: null title is allowed; null result = not a chat. */
    data class Read(val title: String?, val messages: List<Msg>)

    /** Avatar content-desc is "<name>的個人圖片" (zh-Hant; zh-Hans / en guessed). */
    private val AVATAR_SUFFIX = Regex("""(的個人圖片|的个人图片|'s profile (image|photo|picture))$""", RegexOption.IGNORE_CASE)

    fun speakerFromAvatar(desc: String?): String? =
        desc?.trim()?.takeIf { AVATAR_SUFFIX.containsMatchIn(it) }
            ?.replace(AVATAR_SUFFIX, "")?.trim()?.takeIf { it.isNotEmpty() }

    fun read(root: UiNode, width: Int): Read? {
        var inChat = false
        var title: String? = null
        val rows = ArrayList<UiNode>()
        walk(root) { n ->
            when (n.id) {
                ID_INPUT, ID_LIST -> inChat = true
                ID_TITLE -> if (title == null) n.text?.takeIf { it.isNotBlank() }?.let { title = it }
                ID_ROW -> { rows.add(n); return@walk false } // row handled as a unit
            }
            true
        }
        if (!inChat) return null
        // Group chats: only the first row of a run from one person carries the
        // avatar (whose content-desc names them); later rows of that run inherit it.
        // A row of mine ends the run, so an avatar-less row after it stays unnamed
        // rather than being pinned on the wrong person.
        var runSpeaker: String? = null
        val messages = rows.sortedBy { it.top }.mapNotNull { row ->
            val m = message(row, width) ?: return@mapNotNull null
            if (m.side == "me") { runSpeaker = null; m }
            else {
                val who = m.speaker ?: runSpeaker
                runSpeaker = who
                m.copy(speaker = who)
            }
        }
        return Read(title, messages)
    }

    private fun message(row: UiNode, width: Int): Msg? {
        var body: String? = null
        var mine = false
        var other = false
        var speaker: String? = null
        var bubbleLeft = Int.MAX_VALUE
        var bubbleRight = Int.MIN_VALUE
        walk(row) { n ->
            val content = when (n.id) {
                ID_TEXT -> n.text?.takeIf { it.isNotBlank() }
                ID_IMAGE -> PHOTO
                ID_STICKER -> STICKER
                else -> null
            }
            if (content != null) {
                if (body == null) body = content
                bubbleLeft = minOf(bubbleLeft, n.left)
                bubbleRight = maxOf(bubbleRight, n.right)
            }
            when (n.id) {
                ID_MINE_META, ID_READ -> mine = true
                ID_OTHER_META -> other = true
                ID_AVATAR -> { other = true; speaker = speaker ?: speakerFromAvatar(n.desc) }
            }
            true
        }
        val text = body ?: return null
        val side = when {
            mine && !other -> "me"
            other && !mine -> "other"
            // No (or conflicting) markers: my bubbles hug the right edge.
            else -> if (width - bubbleRight < bubbleLeft) "me" else "other"
        }
        return Msg(side, text, if (side == "other") speaker else null)
    }

    /** Depth-first; [visit] returns false to skip a node's children. */
    private fun walk(root: UiNode, visit: (UiNode) -> Boolean) {
        val stack = ArrayDeque<UiNode>()
        stack.addLast(root)
        var guard = 0
        while (stack.isNotEmpty() && guard < 5000) {
            guard++
            val n = stack.removeLast()
            if (visit(n)) for (i in n.children.indices.reversed()) stack.addLast(n.children[i])
        }
    }
}
