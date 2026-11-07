package eu.kanade.tachiyomi.ui.organizer

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class OrganizerRulesTest {
    @Test fun allSelectedRulesMustMatch() {
        val rule = CollectionRule("Offline unread", unread = true, downloaded = true)
        assertTrue(rule.matches(3, 1, false))
        assertFalse(rule.matches(0, 1, false))
        assertFalse(rule.matches(3, 0, true))
        assertTrue(CollectionRule("Completed", completed = true).matches(0, 0, true))
        assertFalse(CollectionRule("Completed", completed = true).matches(3, 1, false))
    }
    @Test fun addingTwicePreservesPositionAndOtherEntries() {
        assertEquals(listOf(8L, 3L), addToQueue(listOf(8L, 3L), 8L))
        assertEquals(listOf(8L, 3L, 4L), addToQueue(listOf(8L, 3L), 4L))
    }
    @Test fun reorderHandlesBoundariesAndMissingIds() {
        val queue = listOf(8L, 3L, 4L)
        assertEquals(listOf(3L, 8L, 4L), moveInQueue(queue, 3L, -1))
        assertEquals(listOf(8L, 4L, 3L), moveInQueue(queue, 3L, 1))
        assertEquals(queue, moveInQueue(queue, 8L, -1))
        assertEquals(queue, moveInQueue(queue, 4L, 1))
        assertEquals(queue, moveInQueue(queue, 99L, -1))
        assertEquals(emptyList<Long>(), moveInQueue(emptyList(), 1, 1))
    }
}

