package com.jev.probe.capture

import com.jev.probe.core.Msg
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.w3c.dom.Element
import javax.xml.parsers.DocumentBuilderFactory

/** Runs [LineExtractor] against a real LINE chat-room dump (names and text replaced). */
class LineExtractorTest {

    private companion object { const val NAME = "測試聯絡人(洗車)" }

    private class XmlNode(
        override val id: String?,
        override val text: String?,
        override val desc: String?,
        override val left: Int,
        override val top: Int,
        override val right: Int,
        override val children: List<UiNode>,
    ) : UiNode

    private fun load(name: String): UiNode {
        val stream = javaClass.classLoader!!.getResourceAsStream(name)!!
        val doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(stream)
        val first = doc.documentElement.getElementsByTagName("node").item(0) as Element
        return toNode(first)
    }

    private fun toNode(e: Element): UiNode {
        val b = Regex("""\[(\d+),(\d+)]\[(\d+),(\d+)]""").find(e.getAttribute("bounds"))!!
            .groupValues.drop(1).map { it.toInt() }
        val kids = (0 until e.childNodes.length)
            .map { e.childNodes.item(it) }
            .filterIsInstance<Element>()
            .filter { it.tagName == "node" }
            .map { toNode(it) }
        return XmlNode(
            id = e.getAttribute("resource-id").ifEmpty { null },
            text = e.getAttribute("text").ifEmpty { null },
            desc = e.getAttribute("content-desc").ifEmpty { null },
            left = b[0], top = b[1], right = b[2], children = kids,
        )
    }

    private fun node(
        id: String?, left: Int, right: Int, top: Int = 0, text: String? = null,
        kids: List<UiNode> = emptyList(), desc: String? = null,
    ): UiNode = XmlNode(id, text, desc, left, top, right, kids)

    @Test
    fun readsTitleAndEveryRowInOrderWithTheRightSide() {
        val read = LineExtractor.read(load("line/chat_1440x3120.xml"), 1440)!!

        assertEquals("測試聯絡人(洗車)", read.title)
        assertEquals(
            listOf(
                Msg("other", "您好\n連假都客滿了\n要排在連假後", NAME),
                // No avatar on a run's second row: the speaker carries over.
                Msg("other", LineExtractor.PHOTO, NAME),
                Msg("me", "好，那約下週六下午，週日也可以嗎？"),
                Msg("other", "可以的\n一天一台好了", NAME),
                Msg("me", "好，謝謝"),
                Msg("other", LineExtractor.STICKER, NAME),
            ),
            read.messages,
        )
    }

    @Test
    fun aScreenWithoutComposeBoxOrMessageListIsNotAChat() {
        val listScreen = node(null, 0, 1440, kids = listOf(
            node("${LineExtractor.PKG}:id/header_title", 180, 799, text = "聊天"),
        ))
        assertNull(LineExtractor.read(listScreen, 1440))
    }

    @Test
    fun aChatWithNoReadableRowsIsAnEmptySnapshotForOcrFallback() {
        val chat = node(null, 0, 1440, kids = listOf(node(LineExtractor.ID_INPUT, 529, 1076)))
        val read = LineExtractor.read(chat, 1440)!!
        assertEquals(emptyList<Msg>(), read.messages)
    }

    @Test
    fun geometryDecidesOnlyWhenARowHasNoSideMarker() {
        fun row(top: Int, left: Int, right: Int) = node(LineExtractor.ID_ROW, 0, 1440, top, kids = listOf(
            node(LineExtractor.ID_TEXT, left, right, top, text = "t$top"),
        ))
        val chat = node(null, 0, 1440, kids = listOf(
            node(LineExtractor.ID_LIST, 0, 1440, kids = listOf(row(100, 977, 1409), row(200, 165, 1012))),
            node(LineExtractor.ID_INPUT, 529, 1076),
        ))
        assertEquals(listOf(Msg("me", "t100"), Msg("other", "t200")), LineExtractor.read(chat, 1440)!!.messages)
    }

    private fun otherRow(top: Int, text: String, avatarOf: String?): UiNode =
        node(LineExtractor.ID_ROW, 0, 1440, top, kids = listOfNotNull(
            avatarOf?.let { node("${LineExtractor.PKG}:id/chat_ui_row_thumbnail", 31, 146, top, desc = "${it}的個人圖片") },
            node(LineExtractor.ID_TEXT, 165, 900, top, text = text),
            node("${LineExtractor.PKG}:id/chat_ui_row_layout_metadata", 920, 1100, top),
        ))

    private fun myRow(top: Int, text: String): UiNode =
        node(LineExtractor.ID_ROW, 0, 1440, top, kids = listOf(
            node("${LineExtractor.PKG}:id/chat_ui_linear_layout_meta_data", 700, 900, top),
            node(LineExtractor.ID_TEXT, 977, 1409, top, text = text),
        ))

    @Test
    fun groupRowsAreAttributedToTheirSpeakerAndRunsInheritIt() {
        val chat = node(null, 0, 1440, kids = listOf(
            node(LineExtractor.ID_LIST, 0, 1440, kids = listOf(
                otherRow(100, "a1", "阿明"),
                otherRow(200, "a2", null),
                otherRow(300, "b1", "小華"),
                myRow(400, "m1"),
                otherRow(500, "?", null),
            )),
            node(LineExtractor.ID_INPUT, 529, 1076),
        ))
        assertEquals(
            listOf(
                Msg("other", "a1", "阿明"),
                Msg("other", "a2", "阿明"),
                Msg("other", "b1", "小華"),
                Msg("me", "m1"),
                // After my message an avatar-less row stays unnamed, never guessed.
                Msg("other", "?", null),
            ),
            LineExtractor.read(chat, 1440)!!.messages,
        )
    }

    @Test
    fun avatarDescriptionYieldsTheName() {
        assertEquals("阿明", LineExtractor.speakerFromAvatar("阿明的個人圖片"))
        assertEquals("Ming", LineExtractor.speakerFromAvatar("Ming's profile image"))
        assertNull(LineExtractor.speakerFromAvatar("貼圖"))
        assertNull(LineExtractor.speakerFromAvatar(null))
    }
}
