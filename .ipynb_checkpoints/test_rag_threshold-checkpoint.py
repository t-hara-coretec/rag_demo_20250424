#!/usr/bin/env python

from rag_utils.rag_service import RagService
import os
import shutil

# Set up test directory
test_dir = './test_docs'
os.makedirs(test_dir, exist_ok=True)

# Create test document
with open(f'{test_dir}/test_doc.txt', 'w') as f:
    f.write("""This is a test document about Python programming language.
Python is widely used for machine learning and AI development.
It's also popular for data analysis and web development.
Machine learning concepts include neural networks, deep learning, and reinforcement learning.""")

# Clean up previous database
if os.path.exists('./test_chroma_db'):
    shutil.rmtree('./test_chroma_db')

# Initialize RAG service with the test directory
print("Initializing RAG service...")
service = RagService(
    pdf_dir=test_dir,
    collection_name='test_cosine_collection',
    chroma_db_dir='./test_chroma_db'
)

# Test with different threshold values
for threshold in [0.0, 0.4, 0.7]:
    print(f"\n=== Testing with threshold {threshold} ===")
    context = service.retrieve_context("What is Python?", retrieve_score_thresh=threshold)
    print(context)