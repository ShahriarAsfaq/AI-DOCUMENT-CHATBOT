from django.core.management.base import BaseCommand
from django.conf import settings
from ai_chatbot.documents.models import Document
from ai_chatbot.rag.document_loader import load_document
from ai_chatbot.rag.chunker import split_into_chunks
from ai_chatbot.rag.document import Document as RagDocument
from ai_chatbot.rag.embeddings import get_embedding_service
from ai_chatbot.rag.vector_store import FaissVectorStore
from ai_chatbot.rag.utils import generate_document_summary, extract_document_topics
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process uploaded documents and build vector store with robust RAG pipeline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Rebuild vector store from scratch',
        )

    def handle(self, *args, **options):
        self.stdout.write('Processing documents and building vector store with robust RAG pipeline...')

        # prepare LLM service for summary/topic generation
        llm_service = None
        try:
            from ai_chatbot.rag.llm_service import GroqLLMService, MockLLMService
            llm_service = GroqLLMService(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")
        except Exception:
            logger.warning("Could not initialize GroqLLMService - falling back to mock")
            from ai_chatbot.rag.llm_service import MockLLMService
            llm_service = MockLLMService()

        # Get all uploaded documents
        documents = Document.objects.all()

        if not documents:
            self.stdout.write(self.style.WARNING('No documents found to process'))
            return

        all_chunks = []
        total_pages = 0
        total_valid_chunks = 0

        # document-level metadata (summary/topics/chunks)
        document_metadata = {}

        # 1. DOCUMENT LOADING
        self.stdout.write('Step 1: Loading and extracting text from documents...')

        for doc in documents:
            try:
                self.stdout.write(f'Processing document: {doc.title}')

                # Get full file path
                file_path = Path(settings.MEDIA_ROOT) / doc.file.name

                if not file_path.exists():
                    self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
                    continue

                # Load document with OCR fallback
                doc_pages = load_document(str(file_path))
                total_pages += len(doc_pages)

                self.stdout.write(f'  - Extracted {len(doc_pages)} pages')

                # Log page content lengths
                for i, page in enumerate(doc_pages):
                    content_length = len(page.page_content.strip())
                    extraction_method = page.metadata.get('extraction_method', 'unknown')
                    self.stdout.write(f'    Page {i+1}: {content_length} chars ({extraction_method})')

                # combine full text for summary/topics
                full_text = "\n\n".join(p.page_content for p in doc_pages)
                summary = generate_document_summary(full_text, llm_service)
                topics = extract_document_topics(full_text, llm_service)
                # store in document metadata map
                document_metadata[doc.id] = {
                    "summary": summary,
                    "topics": topics,
                    "chunks": [],
                }
                logger.info("Document summary generated for '%s'", doc.title)
                logger.info("Topics extracted: %d", len(topics))
                if topics:
                    logger.info("Topic list: %s", "; ".join(topics))

                # Convert to RagDocument objects for chunking
                rag_docs = []
                for page_doc in doc_pages:
                    rag_docs.append(RagDocument(
                        page_content=page_doc.page_content,
                        metadata=page_doc.metadata
                    ))

                # 4. CHUNKING with RecursiveCharacterTextSplitter
                self.stdout.write('Step 4: Chunking documents...')
                chunks = split_into_chunks(rag_docs, chunk_size=500, chunk_overlap=100)

                # 5. CHUNK VALIDATION
                valid_chunks = []
                for chunk in chunks:
                    if len(chunk.page_content.strip()) >= 20:  # Minimum meaningful content
                        valid_chunks.append(chunk)
                        all_chunks.append({
                            'text': chunk.page_content,
                            'metadata': {
                                'source': doc.title,
                                'page': chunk.metadata.get('page', 1),
                                'chunk_text': chunk.page_content,
                                'document_id': doc.id,
                                'chunk_index': chunk.metadata.get('chunk_index', 0),
                            }
                        })

                total_valid_chunks += len(valid_chunks)
                self.stdout.write(f'  - Created {len(valid_chunks)} valid chunks from {len(chunks)} raw chunks')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing {doc.title}: {str(e)}'))
                logger.exception(f"Error processing document {doc.title}")
                continue

        if not all_chunks:
            self.stdout.write(self.style.ERROR('No valid chunks created from documents'))
            return

        # 6. EMBEDDING
        self.stdout.write('Step 6: Generating embeddings...')
        try:
            embedding_service = get_embedding_service()

            texts = [chunk['text'] for chunk in all_chunks]
            embeddings = embedding_service.encode(texts)

            self.stdout.write(f'  - Generated embeddings for {len(texts)} chunks')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating embeddings: {str(e)}'))
            return

        # 7. VECTOR DATABASE
        self.stdout.write('Step 7: Building vector store...')

        try:
            # Clear existing vector store before building new one
            processed_store_path = Path(settings.VECTOR_STORE_PATH) / "faiss_store"
            if processed_store_path.exists():
                import shutil
                shutil.rmtree(processed_store_path)
                self.stdout.write('  - Cleared existing vector store')

            vector_store = FaissVectorStore()

            # Prepare metadata
            metadata_list = [chunk['metadata'] for chunk in all_chunks]

            # Build index
            vector_store.build_index(embeddings, metadata_list)

            # Attach document-level metadata for intent handling
            vector_store.document_metadata = document_metadata

            # Save to processed store
            vector_store.save_index(str(processed_store_path))

            self.stdout.write(self.style.SUCCESS(
                f'Successfully built vector store with {len(all_chunks)} chunks '
                f'from {total_pages} pages across {len(documents)} documents'
            ))

            # 10. DEBUGGING - Log summary
            logger.info("RAG Pipeline Summary:")
            logger.info(f"  - Documents processed: {len(documents)}")
            logger.info(f"  - Total pages extracted: {total_pages}")
            logger.info(f"  - Valid chunks created: {total_valid_chunks}")
            logger.info(f"  - Vector store size: {vector_store.get_index_size()}")

            # Log first 3 chunks as examples
            for i, chunk in enumerate(all_chunks[:3]):
                text_preview = chunk['text'][:150].replace('\n', ' ')
                logger.info(f"  - Sample chunk {i+1}: '{text_preview}...'")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error building vector store: {str(e)}'))
            logger.exception("Error building vector store")