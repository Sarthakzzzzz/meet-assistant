import os
from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
import chromadb.utils.embedding_functions as embedding_functions

class ChromaDefaultEmbeddings:
    def __init__(self):
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.ef(texts)
        
    def embed_query(self, text: str) -> List[float]:
        return self.ef([text])[0]

class MeetingVectorStore:
    def __init__(self, persist_directory: str = "data/chroma_db"):
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        self.embeddings = ChromaDefaultEmbeddings()
        # ISSUE #3: All meetings share a single global collection. Data from different
        # sessions is co-mingled and cannot be queried independently. Needs per-session
        # collections named like meeting_{uuid} with a meeting_id parameter.
        self.vector_store = Chroma(
            collection_name="meeting_context",
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def add_caption(self, speaker: str, text: str, slide_path: str = None):
        # ISSUE #2: Only spoken captions are embedded here. There is no OCR stage to
        # extract and embed text content from captured slide images. The LLM has no
        # awareness of what is displayed on screen, only what was said.
        # Proposed fix: add an OCR pass (e.g. pytesseract) on each slide image in
        # handle_slide_captured() and embed the extracted text alongside captions.
        caption_line = f"{speaker}: {text}"
        doc = Document(
            page_content=caption_line,
            metadata={"speaker": speaker, "slide": slide_path or "pre_slide"}
        )
        self.vector_store.add_documents([doc])

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        return self.vector_store.similarity_search(query, k=k)
