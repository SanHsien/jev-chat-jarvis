package com.jev.probe.jev

import android.graphics.Bitmap
import android.util.Base64
import com.jev.probe.core.Prefs
import java.io.ByteArrayOutputStream
import org.json.JSONArray
import org.json.JSONObject

/**
 * The vision route: an OpenAI-compatible `/chat/completions` endpoint that
 * accepts `image_url` content parts. A-stage shell only — B stage wires it to
 * the screenshot pipeline.
 *
 * Reads visionBaseUrl / visionKey / visionModel from [Prefs]. The base URL does
 * not inherit from the reply route (a text-only host has no vision
 * endpoint); the key still falls back reply -> judge.
 *
 * Wire format notes that cost real debugging time:
 * - JPEG, not PNG: a screenshot as PNG base64 is several times larger.
 * - `Base64.NO_WRAP`: Android's default inserts newlines, which corrupts the
 *   data URL.
 * - The image part goes BEFORE the text part — some OpenAI-compatible hosts
 *   reject the other order.
 */
class VisionClient(private val prefs: Prefs) {

    /**
     * Send a screenshot and get the transcribed dialog back as plain text.
     * B stage will parse this into bubbles; A stage only proves the route works.
     *
     * @param imageBase64Jpeg base64 of a JPEG, without the `data:` prefix.
     */
    fun extractDialog(imageBase64Jpeg: String): String = ask(
        imageBase64Jpeg,
        "你是聊天截圖轉寫助手。把圖中聊天氣泡按從上到下的順序轉寫成文字，" +
            "每行一條，格式 `我：正文` 或 `對方：正文`。只輸出轉寫結果，不要解釋。"
    )

    /** Generic single-question call against the image (used by the settings test). */
    fun ask(imageBase64Jpeg: String, prompt: String): String {
        val url = prefs.visionEndpoint()
        // Image first, then text: some compatible hosts require this order.
        val content = JSONArray()
            .put(JSONObject()
                .put("type", "image_url")
                .put("image_url", JSONObject().put("url", "data:image/jpeg;base64,$imageBase64Jpeg")))
            .put(JSONObject().put("type", "text").put("text", prompt))
        val messages = JSONArray().put(
            JSONObject().put("role", "user").put("content", content))
        val body = JSONObject()
            .put("model", prefs.visionModel)
            .put("messages", messages)
            .put("temperature", 0.0)
        val resp = HttpJson.post(url, prefs.effectiveVisionKey(), body, Route.VISION, HttpJson.headersFor(url))
        return resp.optJSONArray("choices")?.optJSONObject(0)
            ?.optJSONObject("message")?.optString("content") ?: ""
    }

    companion object {
        /** Bitmap -> JPEG base64 in the exact form [ask] expects. */
        fun encodeJpeg(bitmap: Bitmap, quality: Int = 80): String {
            val out = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.JPEG, quality, out)
            return Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
        }
    }
}
