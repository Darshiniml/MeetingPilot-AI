import logging
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.error import HTTPError, URLError

from app.ai.providers import LLMProvider
from app.repositories.transcript_repository import TranscriptRepository
from app.repositories.vector_repository import (
    VectorDocumentDraft,
    VectorRepository,
)
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TranscriptRetrievalChunk:
    transcript_id: int
    content: str


class TranscriptChunker:
    """Split transcript records into bounded semantic retrieval chunks."""

    def __init__(self, maximum_characters: int = 800) -> None:
        self._maximum_characters = maximum_characters

    def split(self, *, transcript_id: int, text: str) -> Sequence[TranscriptRetrievalChunk]:
        words = text.split()
        if not words:
            return ()
        chunks: list[str] = []
        current: list[str] = []
        current_length = 0
        for word in words:
            additional_length = len(word) + (1 if current else 0)
            if current and current_length + additional_length > self._maximum_characters:
                chunks.append(" ".join(current))
                current = []
                current_length = 0
            current.append(word)
            current_length += len(word) + (1 if len(current) > 1 else 0)
        if current:
            chunks.append(" ".join(current))
        return tuple(
            TranscriptRetrievalChunk(transcript_id=transcript_id, content=chunk)
            for chunk in chunks
        )


class LocalModelUnavailableError(RuntimeError):
    """Raised when the configured local Ollama models cannot serve chat."""


class ChatService:
    """Index transcripts locally, retrieve relevant context, and answer via Ollama."""

    def __init__(
        self,
        transcript_repository: TranscriptRepository,
        vector_repository: VectorRepository,
        embedding_service: EmbeddingService,
        llm_provider: LLMProvider,
        *,
        top_k: int = 4,
        chunker: TranscriptChunker | None = None,
    ) -> None:
        self._transcript_repository = transcript_repository
        self._vector_repository = vector_repository
        self._embedding_service = embedding_service
        self._llm_provider = llm_provider
        self._top_k = top_k
        self._chunker = chunker or TranscriptChunker()

    def answer_question(self, *, meeting_id: int, question: str) -> str:
        """Return an Ollama answer grounded only in top-ranked meeting context."""
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")
        chunks = tuple(
            retrieval_chunk
            for transcript in self._transcript_repository.list_transcripts_for_meeting(meeting_id)
            for retrieval_chunk in self._chunker.split(
                transcript_id=transcript.id, text=transcript.text
            )
        )
        if not chunks:
            raise ValueError("Meeting has no transcript content to search")
        try:
            print("Embedding started", flush=True)
            logger.info("Embedding started")
            embeddings = self._embedding_service.embed_texts([chunk.content for chunk in chunks])
            self._vector_repository.replace_for_meeting(
                meeting_id=meeting_id,
                documents=tuple(
                    VectorDocumentDraft(
                        transcript_id=chunk.transcript_id,
                        chunk_index=index,
                        content=chunk.content,
                        embedding=embedding,
                    )
                    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
                ),
            )
            print("Embedding stored", flush=True)
            logger.info("Embedding stored")
            question_embedding = self._embedding_service.embed_texts([question])[0]
            context = self._vector_repository.retrieve_top_k(
                meeting_id=meeting_id,
                query_embedding=question_embedding,
                top_k=self._top_k,
            )
            if not context:
                raise ValueError("Meeting has no searchable transcript content")
            return self._llm_provider.generate(
                self._build_answer_prompt(
                    question=question, context=[item.content for item in context]
                )
            ).content
        except (HTTPError, URLError) as error:
            raise LocalModelUnavailableError(
                "The configured local Ollama model is unavailable. "
                "Install the embedding model with: ollama pull nomic-embed-text"
            ) from error

    @staticmethod
    def _build_answer_prompt(*, question: str, context: Sequence[str]) -> str:
        joined_context = "\n\n".join(f"- {item}" for item in context)
        return (
            "Answer the question using only the retrieved meeting context. "
            "If the answer is not contained in the context, say so plainly.\n\n"
            f"Question:\n{question}\n\nRetrieved Context:\n{joined_context}"
        )
