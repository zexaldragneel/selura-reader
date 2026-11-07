package eu.kanade.tachiyomi.ui.organizer

internal data class CollectionRule(
    val name: String,
    val unread: Boolean = false,
    val downloaded: Boolean = false,
    val completed: Boolean = false,
) {
    fun matches(unreadCount: Long, downloadCount: Int, isCompleted: Boolean): Boolean =
        (!unread || unreadCount > 0) && (!downloaded || downloadCount > 0) && (!completed || isCompleted)
}

internal fun moveInQueue(queue: List<Long>, id: Long, offset: Int): List<Long> {
    val index = queue.indexOf(id)
    val target = index + offset
    if (index < 0 || target !in queue.indices) return queue
    return queue.toMutableList().apply { add(target, removeAt(index)) }
}

internal fun addToQueue(queue: List<Long>, id: Long): List<Long> =
    if (id in queue) queue else queue + id

