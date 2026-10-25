package com.jev.probe.jev

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class HardTimeoutTest {

    @Test
    fun fastCallReturnsItsValue() {
        assertEquals(42, withHardTimeout(1_000) { 42 })
    }

    @Test
    fun stuckCallIsAbandonedAfterTheCeiling() {
        // A lookup that never comes back must surface as a plain error, not hang the round.
        assertThrows(HardTimeoutException::class.java) {
            withHardTimeout(50) { Thread.sleep(10_000); 1 }
        }
    }

    @Test
    fun interruptedCallerGetsAnIoErrorNotARawInterrupt() {
        val t = Thread.currentThread()
        Thread { Thread.sleep(100); t.interrupt() }.start()
        try {
            assertThrows(HardTimeoutException::class.java) {
                withHardTimeout(10_000) { Thread.sleep(10_000); 1 }
            }
        } finally {
            Thread.interrupted() // clear the flag restored by withHardTimeout
        }
    }

    @Test
    fun callerSeesTheOriginalException() {
        val e = assertThrows(IllegalStateException::class.java) {
            withHardTimeout(1_000) { throw IllegalStateException("boom") }
        }
        assertEquals("boom", e.message)
    }
}
