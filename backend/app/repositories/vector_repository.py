"""SQLite persistence and cosine-similarity retrieval for local vectors."""

from collections.abc import Sequence
from dataclasses import dataclass
import json
from math import sqrt

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.vector_embedding import VectorEmbedding


@dataclass(frozen=True, slots=True)
class VectorDocumentDraft:
    transcript_id: int
    chunk_index: int
    content: str
    embedding: Sequence[float]


@dataclass(frozen=True, slots=True)
class RetrievedVectorDocument:
    content: str
    score: float


class VectorRepository:
    """Store local embeddings and retrieve relevant meeting context."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_for_meeting(
        self, *, meeting_id: int, documents: Sequence[VectorDocumentDraft]
    ) -> None:
        """Replace a meeting's index atomically with freshly embedded chunks."""
        self._session.execute(
            delete(VectorEmbedding).where(VectorEmbedding.meeting_id == meeting_id)
        )
        self._session.add_all(
            VectorEmbedding(
                meeting_id=meeting_id,
                transcript_id=document.transcript_id,
                chunk_index=document.chunk_index,
                content=document.content,
                embedding=json.dumps(list(document.embedding)),
            )
            for document in documents
        )
        try:
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise

    def retrieve_top_k(
        self, *, meeting_id: int, query_embedding: Sequence[float], top_k: int
    ) -> Sequence[RetrievedVectorDocument]:
        """Rank stored meeting chunks by cosine similarity to the question vector."""
        if top_k < 1:
            raise ValueError("top_k must be at least one")
        statement = (
            select(VectorEmbedding)
            .where(VectorEmbedding.meeting_id == meeting_id)
            .order_by(VectorEmbedding.chunk_index.asc())
        )
        matches = []
        for document in self._session.execute(statement).scalars():
            embedding = json.loads(document.embedding)
            if len(embedding) != len(query_embedding):
                continue
            matches.append(
                RetrievedVectorDocument(
                    content=document.content,
                    score=self._cosine_similarity(query_embedding, embedding),
                )
            )
        return tuple(sorted(matches, key=lambda item: item.score, reverse=True)[:top_k])

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
