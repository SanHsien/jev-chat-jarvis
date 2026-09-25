package com.jev.probe.jev

import org.junit.Assert.assertEquals
import org.junit.Test

class ReplyLineParserTest {
    @Test
    fun preservesLeadingNumbers() {
        assertEquals(
            listOf("2點見", "30分鐘後到", "123號門口等你"),
            ReplyLineParser.parse("2點見\n30分鐘後到\n123號門口等你")
        )
    }

    @Test
    fun removesNumberedPrefixWithoutEatingReplyText() {
        assertEquals(
            listOf("2點見", "30分鐘後到", "123號門口等你"),
            ReplyLineParser.parse("1. 2點見\n2. 30分鐘後到\n3. 123號門口等你")
        )
    }

    @Test
    fun preservesDecimalNumbers() {
        assertEquals(
            listOf("1.5小時後到", "2.0版本已經更新", "3.14不是3.15"),
            ReplyLineParser.parse("1.5小時後到\n2.0版本已經更新\n3.14不是3.15")
        )
    }

    @Test
    fun preservesNegativeNumbers() {
        assertEquals(
            listOf("-2度，記得加衣服", "-3.5這個數沒算錯", "-10也可以"),
            ReplyLineParser.parse("-2度，記得加衣服\n-3.5這個數沒算錯\n-10也可以")
        )
    }

    @Test
    fun removesBulletPrefixes() {
        assertEquals(
            listOf("2點見", "30分鐘後到", "1.5小時後到"),
            ReplyLineParser.parse("- 2點見\n* 30分鐘後到\n- 1.5小時後到")
        )
    }

    @Test
    fun removesNumberPrefixesWithClosingParenthesis() {
        assertEquals(
            listOf("2點見", "30分鐘後到", "123號門口等你"),
            ReplyLineParser.parse("1) 2點見\n2) 30分鐘後到\n3) 123號門口等你")
        )
    }

    @Test
    fun keepsAmbiguousPrefixes() {
        assertEquals(
            listOf("1.明天見", "*這句話先保留", "2026. 9月再說"),
            ReplyLineParser.parse("1.明天見\n*這句話先保留\n2026. 9月再說")
        )
    }

    @Test
    fun removesOnlyOnePrefix() {
        assertEquals(
            listOf("2. 先確認時間", "* 這部分是正文", "- 這部分也是正文"),
            ReplyLineParser.parse("1. 2. 先確認時間\n- * 這部分是正文\n* - 這部分也是正文")
        )
    }

    @Test
    fun handlesWhitespaceAndCrLf() {
        assertEquals(
            listOf("2點見", "30分鐘後到", "好的"),
            ReplyLineParser.parse("  1.\t2點見  \r\n\t*\t30分鐘後到\r\n 好的 \r\n")
        )
    }

    @Test
    fun skipsBlankLinesAndEmptyListItems() {
        assertEquals(
            listOf("收到", "好", "明天見"),
            ReplyLineParser.parse("\n  \n1. \n- \n*\n2) \n收到\n\n好\n明天見\n")
        )
    }

    @Test
    fun padsMissingReplies() {
        assertEquals(
            listOf("2點見", "（稍等，我看下）", "（稍等，我看下）"),
            ReplyLineParser.parse("2點見")
        )
    }

    @Test
    fun keepsOnlyTheFirstThreeReplies() {
        assertEquals(listOf("收到", "好", "明天見"), ReplyLineParser.parse("收到\n好\n明天見\n不保留這條"))
    }

    @Test
    fun keepsExistingEmptyInputFallback() {
        assertEquals(List(3) { "（稍等，我看下）" }, ReplyLineParser.parse(" \n\t\n"))
    }

    @Test
    fun keepsOpeningQuoteCleanupWithoutStrippingNumbers() {
        assertEquals(
            listOf("2點見", "30分鐘後到", "123號門口等你"),
            ReplyLineParser.parse("\"2點見\n1. \"30分鐘後到\n\"2. 123號門口等你")
        )
    }
}
