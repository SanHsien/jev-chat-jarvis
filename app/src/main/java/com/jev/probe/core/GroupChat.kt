package com.jev.probe.core

/**
 * Group-chat helpers (original to this fork). An adapter that can name the other
 * side's speakers fills [Msg.speaker]; everything here is derived from that, so a
 * 1:1 chat -- or an adapter that never names anyone -- behaves exactly as before.
 */

/** Title suffix like "(12)" / "（12）" that group rooms show. */
private val MEMBER_COUNT = Regex("""[（(]\d+[）)]\s*$""")

/** Distinct named speakers on the other side, oldest first. */
fun ChatSnapshot.otherSpeakers(): List<String> =
    messages.filter { it.side == "other" }.mapNotNull { it.speaker }.distinct()

/** Two or more named people on the other side, or a member-count title. */
fun ChatSnapshot.isGroupChat(): Boolean =
    otherSpeakers().size >= 2 || (title?.let { MEMBER_COUNT.containsMatchIn(it) } ?: false)

/**
 * Whom the analysis is about: the sender of the newest message from the other side
 * (the person the user would be answering). Null when that message is unnamed.
 */
fun ChatSnapshot.focusSpeaker(): String? =
    messages.lastOrNull { it.side == "other" }?.speaker
