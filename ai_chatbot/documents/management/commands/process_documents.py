from django.core.management.base import BaseCommand
from django.conf import settings
from ai_chatbot.documents.models import Document
from ai_chatbot.rag.document_loader import load_document
from ai_chatbot.rag.chunker import split_into_chunks
from ai_chatbot.rag.document import Document as RagDocument
from ai_chatbot.rag.utils import get_vector_store
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Process uploaded documents and build vector store'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Rebuild vector store from scratch',
        )

    def handle(self, *args, **options):
        self.stdout.write('Processing documents and building vector store...')

        # Get all uploaded documents
        documents = Document.objects.all()

        if not documents:
            self.stdout.write(self.style.WARNING('No documents found to process'))
            return

        all_texts = []
        all_metadata = []

        for doc in documents:
            try:
                self.stdout.write(f'Processing document: {doc.title}')

                # Get full file path
                file_path = Path(settings.MEDIA_ROOT) / doc.file.name

                if not file_path.exists():
                    self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
                    continue

                # Load document
                doc_pages = load_document(str(file_path))

                # Convert to RagDocument objects for chunking
                rag_docs = []
                for page_doc in doc_pages:
                    rag_docs.append(RagDocument(
                        page_content=page_doc.page_content,
                        metadata=page_doc.metadata
                    ))

                # Chunk the documents
                chunks = split_into_chunks(rag_docs, chunk_size=800, chunk_overlap=200)

                for chunk in chunks:
                    all_texts.append(chunk.page_content)
                    all_metadata.append({
                        'source': doc.title,
                        'page': chunk.metadata.get('page', 1),
                        'chunk_text': chunk.page_content,
                        'document_id': doc.id,
                    })

                self.stdout.write(f'  - Processed {len(doc_pages)} pages, created {len(chunks)} chunks')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing {doc.title}: {str(e)}'))
                continue

        if not all_texts:
            self.stdout.write(self.style.ERROR('No text content extracted from documents'))
            return

        self.stdout.write(f'Building vector store with {len(all_texts)} chunks...')

        # Build vector store
        try:
            vector_store = get_vector_store(all_texts, all_metadata, persist=True)
            self.stdout.write(self.style.SUCCESS(f'Successfully built vector store with {len(all_texts)} chunks'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error building vector store: {str(e)}'))