from django.core.management.base import BaseCommand
from django.conf import settings
from ai_chatbot.rag.vector_store import FaissVectorStore
import os

class Command(BaseCommand):
    help = 'Verify that FAISS vector store exists; rebuild if missing or empty.'

    def handle(self, *args, **options):
        # ensure any raw files placed directly in media/docs are registered
        docs_dir = os.path.join(settings.MEDIA_ROOT, 'docs')
        if os.path.isdir(docs_dir):
            from ai_chatbot.documents.models import Document
            for fname in os.listdir(docs_dir):
                path = os.path.join(docs_dir, fname)
                if os.path.isfile(path):
                    title = os.path.splitext(fname)[0]
                    relpath = os.path.join('docs', fname)
                    obj, created = Document.objects.get_or_create(
                        title=title,
                        defaults={'file': relpath},
                    )
                    if created:
                        self.stdout.write(f'Registered new Document for file {relpath}')

        store_path = os.path.join(settings.VECTOR_STORE_PATH, 'faiss_store')
        self.stdout.write(f'Checking FAISS vector store at {store_path}')
        store = FaissVectorStore()
        try:
            store.load_index(store_path)
            size = store.get_index_size()
            if size == 0:
                self.stdout.write('Vector store loaded but empty; rebuilding via process_documents')
                from django.core.management import call_command
                call_command('process_documents')
            else:
                self.stdout.write(f'Vector store OK ({size} vectors)')
        except Exception as e:
            self.stdout.write(f'Could not load existing store: {e}')
            self.stdout.write('Running process_documents to create store')
            from django.core.management import call_command
            call_command('process_documents')
