"""Portable ID-based read-only access to the complete FinRisk knowledge corpus.

Build: python -S -X utf8 -B full_reader.py build --source-root ROOT --target NEW_DIR
Use the returned manifest fingerprint and five versions as an external trust anchor.
"""
from full_reader_task.reader import FullKnowledgeReader
from full_reader_task.builder import build_full_reader,build_index,main

__all__=['FullKnowledgeReader','build_full_reader','build_index']

if __name__=='__main__':main()
