"""Background memory compaction merging duplicates and consolidating low-value entries."""

import logging
import json
from typing import Any
from app.memory.memory_models import Memory
from app.memory.memory_repository import MemoryRepository
from app.memory.vector_store import cosine_similarity

logger = logging.getLogger(__name__)


class MemoryCompactor:
    """Consolidates highly similar or redundant semantic memory entries."""

    def __init__(self, repository_factory, similarity_threshold: float = 0.88) -> None:
        self._repository_factory = repository_factory
        self._similarity_threshold = similarity_threshold

    def compact(self, user_id: int) -> int:
        """Scan all memory records for user_id, merge duplicates, and return total count of merged entries."""
        logger.info("Executing memory compaction for user=%d", user_id)
        savings = 0

        with self._repository_factory() as session:
            repo = MemoryRepository(session)
            memories = list(repo.list_memories(user_id=user_id))
            
            # Group memories by type
            grouped: dict[str, list[Memory]] = {}
            for m in memories:
                grouped.setdefault(m.memory_type, []).append(m)

            deleted_ids = set()

            for memory_type, memory_list in grouped.items():
                n = len(memory_list)
                for i in range(n):
                    m1 = memory_list[i]
                    if m1.memory_id in deleted_ids:
                        continue

                    v1 = json.loads(m1.embedding) if m1.embedding else None
                    if not v1:
                        continue

                    for j in range(i + 1, n):
                        m2 = memory_list[j]
                        if m2.memory_id in deleted_ids:
                            continue

                        v2 = json.loads(m2.embedding) if m2.embedding else None
                        if not v2:
                            continue

                        # Check similarity
                        sim = cosine_similarity(v1, v2)
                        if sim >= self._similarity_threshold:
                            logger.info(
                                "Compactor merging duplicate memories: type=%s, id1=%s, id2=%s, sim=%.3f",
                                memory_type, m1.memory_id, m2.memory_id, sim
                            )
                            # Keep m1, merge m2 into it
                            m1.importance_score = max(m1.importance_score, m2.importance_score)
                            m1.access_count += m2.access_count
                            
                            # Merge contents if they diverge
                            if m1.content.strip().casefold() != m2.content.strip().casefold():
                                m1.content = f"{m1.content}\nConcurrently remembered: {m2.content}"
                            
                            # Merge metadata
                            meta1 = json.loads(m1.metadata_json) if m1.metadata_json else {}
                            meta2 = json.loads(m2.metadata_json) if m2.metadata_json else {}
                            meta1.update(meta2)
                            m1.metadata_json = json.dumps(meta1)

                            # Delete m2
                            repo.delete_memory(m2.memory_id)
                            deleted_ids.add(m2.memory_id)
                            savings += 1

            if savings > 0:
                logger.info("Compaction completed successfully. Saved %d rows.", savings)
        return savings
