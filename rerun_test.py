import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','ai_chatbot.settings')
django.setup()
from django.core.management import call_command
from ai_chatbot.settings import get_or_create_chat_service

print('re-running document processing')
call_command('process_documents')
cs = get_or_create_chat_service()
print('got chat service:', cs)
print('summary response:', cs.answer_question('Please summarize the document.'))
