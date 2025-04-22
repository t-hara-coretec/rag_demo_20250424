#!/usr/bin/env python

from rag_utils.vector_store import VectorStore
import os
import shutil

# Clean up previous test data
if os.path.exists('./multi_test_db'):
    shutil.rmtree('./multi_test_db')

# Create a new vector store with cosine similarity
print("Creating vector store...")
store = VectorStore(collection_name='multi_test', data_dir='./multi_test_db')

# Add test documents
test_docs = [
    {'content': 'Python is a high-level programming language with simple syntax.', 'metadata': {'source': 'doc1'}},
    {'content': 'Machine learning is a field of AI that enables systems to learn from data.', 'metadata': {'source': 'doc2'}},
    {'content': 'Python is widely used for data science, web development, and automation.', 'metadata': {'source': 'doc3'}},
    {'content': 'Neural networks are a class of machine learning models inspired by the human brain.', 'metadata': {'source': 'doc4'}},
    {'content': 'JavaScript is a programming language used primarily for web development.', 'metadata': {'source': 'doc5'}}
]

print("Adding test documents...")
store.add_documents(test_docs)

# Test with Python query at different thresholds
query = "What is Python?"
print(f"\nQuerying: {query}")

for threshold in [0.0, 0.5, 0.7]:
    print(f"\n=== Using threshold {threshold} ===")
    # Filter documents manually to simulate the retrieve_context method
    results = store.query(query, top_k=5)
    filtered_results = [doc for doc in results if doc['score'] >= threshold]
    
    print(f"Retrieved {len(results)} documents, filtered to {len(filtered_results)} with threshold {threshold}")
    
    for idx, doc in enumerate(results):
        status = "(kept)" if doc['score'] >= threshold else "(filtered)"
        print(f"Document {idx+1}: score={doc['score']:.4f} {status}, content={doc['content']}")

print("\nTest completed!")