#!/usr/bin/env python

from rag_utils.vector_store import VectorStore
import os
import shutil

# Clean up previous test data
if os.path.exists('./chroma_test'):
    shutil.rmtree('./chroma_test')

# Create a new vector store with cosine similarity
print("Creating vector store...")
store = VectorStore(collection_name='cosine_test', data_dir='./chroma_test')

# Add test documents
test_docs = [
    {'content': 'This is a document about Python programming language.', 'metadata': {'source': 'test1'}},
    {'content': 'This document covers machine learning concepts.', 'metadata': {'source': 'test2'}},
    {'content': 'Python is a popular programming language for AI development.', 'metadata': {'source': 'test3'}}
]

print("Adding test documents...")
store.add_documents(test_docs)

# Test with Python query
query = "What is Python?"
print(f"\nQuerying: {query}")
results = store.query(query, top_k=3)
for idx, doc in enumerate(results):
    print(f"Result {idx+1}: score={doc['score']:.4f}, content={doc['content']}")

# Test with machine learning query
query = "Tell me about machine learning"
print(f"\nQuerying: {query}")
results = store.query(query, top_k=3)
for idx, doc in enumerate(results):
    print(f"Result {idx+1}: score={doc['score']:.4f}, content={doc['content']}")

print("\nTest completed!")