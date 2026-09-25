package com.jev.probe.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GroupChatTest {

    @Test
    fun oneNamedPersonIsNotAGroup() {
        val s = ChatSnapshot("阿明", listOf(Msg("other", "hi", "阿明"), Msg("me", "yo"), Msg("other", "ok", "阿明")))
        assertFalse(s.isGroupChat())
        assertEquals("阿明", s.focusSpeaker())
    }

    @Test
    fun twoNamedPeopleMakeAGroupAndTheLatestOtherSpeakerIsTheFocus() {
        val s = ChatSnapshot("同事", listOf(
            Msg("other", "a", "阿明"), Msg("other", "b", "小華"), Msg("me", "c"),
        ))
        assertTrue(s.isGroupChat())
        assertEquals(listOf("阿明", "小華"), s.otherSpeakers())
        // Latest message is mine: the focus is the last person on the other side.
        assertEquals("小華", s.focusSpeaker())
    }

    @Test
    fun aMemberCountTitleMarksAGroupEvenWithOneVisibleSpeaker() {
        assertTrue(ChatSnapshot("讀書會(12)", listOf(Msg("other", "a", "阿明"))).isGroupChat())
        assertTrue(ChatSnapshot("讀書會（12）", listOf(Msg("other", "a", "阿明"))).isGroupChat())
        assertFalse(ChatSnapshot("王小明(洗車)", listOf(Msg("other", "a", "王小明"))).isGroupChat())
    }

    @Test
    fun unnamedMessagesKeepTheOldBehaviour() {
        val s = ChatSnapshot("x", listOf(Msg("other", "a"), Msg("other", "b")))
        assertFalse(s.isGroupChat())
        assertNull(s.focusSpeaker())
    }
}
