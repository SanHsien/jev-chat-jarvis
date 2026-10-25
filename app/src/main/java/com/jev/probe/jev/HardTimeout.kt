package com.jev.probe.jev

import java.io.IOException
import java.util.concurrent.Callable
import java.util.concurrent.ExecutionException
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException

/**
 * Hard ceiling for one network round.
 *
 * `HttpURLConnection` bounds connect and read per attempt but NOT the DNS lookup,
 * so a single wedged lookup could hold a worker thread (and with it the whole
 * analysis round) forever: the panel sat on "generating" and the busy flag never
 * cleared. The call runs on its own daemon pool; past [timeoutMs] the caller gets
 * an [IOException] it already knows how to show, and the stuck thread is
 * interrupted instead of being waited on.
 */
internal class HardTimeoutException(message: String) : IOException(message)

private val netPool = Executors.newCachedThreadPool { r ->
    Thread(r, "jev-net").apply { isDaemon = true }
}

internal const val HARD_TIMEOUT_MS = 120_000L

internal fun <T> withHardTimeout(timeoutMs: Long = HARD_TIMEOUT_MS, block: () -> T): T {
    val future = netPool.submit(Callable { block() })
    try {
        return future.get(timeoutMs, TimeUnit.MILLISECONDS)
    } catch (e: TimeoutException) {
        future.cancel(true)
        throw HardTimeoutException("請求逾時，請稍後再試")
    } catch (e: ExecutionException) {
        throw e.cause ?: e
    }
}
