package com.jev.probe.core

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RemovedVendorsTest {

    @Test
    fun removedVendorHostsAreRecognised() {
        assertTrue(Prefs.isRemovedHost("https://jev.bocha.cn"))
        assertTrue(Prefs.isRemovedHost("https://api.deepseek.com/v1"))
        assertTrue(Prefs.isRemovedHost("https://dashscope.aliyuncs.com/compatible-mode/v1"))
    }

    @Test
    fun keptHostsAreNotTouched() {
        assertFalse(Prefs.isRemovedHost(null))
        assertFalse(Prefs.isRemovedHost(Prefs.DEFAULT_JUDGE_BASE_VERCEL))
        assertFalse(Prefs.isRemovedHost(Prefs.VERCEL_OPENAI_BASE))
        assertFalse(Prefs.isRemovedHost(Prefs.DEFAULT_REPLY_BASE))
        assertFalse(Prefs.isRemovedHost(Prefs.DEFAULT_JUDGE_BASE_ZEN))
        assertFalse(Prefs.isRemovedHost(Prefs.DEFAULT_JUDGE_BASE_TYPESAFE))
    }

    @Test
    fun removedVendorModelsAreRecognised() {
        assertTrue(Prefs.isRemovedModel("deepseek/deepseek-v3.1"))
        assertTrue(Prefs.isRemovedModel("deepseek/deepseek-chat-v3.1"))
        assertTrue(Prefs.isRemovedModel("qwen/qwen2.5-vl-72b-instruct"))
        assertTrue(Prefs.isRemovedModel("qwen-vl-max"))
    }

    @Test
    fun currentDefaultsAreNotRemovedModels() {
        for (m in listOf(Prefs.DEFAULT_REPLY_MODEL, Prefs.VERCEL_REPLY_MODEL,
                Prefs.DEFAULT_VISION_MODEL, Prefs.VERCEL_VISION_MODEL,
                Prefs.DEFAULT_JUDGE_MODEL_VERCEL, Prefs.DEFAULT_JUDGE_MODEL_OPENROUTER)) {
            assertFalse(m, Prefs.isRemovedModel(m))
        }
    }
}
