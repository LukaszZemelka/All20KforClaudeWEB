#!/usr/bin/env python3
"""
Apply generated sentences from JSON file to CSV.
"""

import csv
import json
import sys
import re

def count_words(sentence):
    """Count words in a sentence."""
    words = re.findall(r'\b\w+\b', sentence)
    return len(words)

def validate_sentence(sentence, word):
    """Validate sentence meets requirements."""
    errors = []

    # Check word count
    word_count = count_words(sentence)
    if word_count < 4 or word_count > 13:
        errors.append(f"Word count {word_count} not in 4-13 range")

    # Check word is present
    word_lower = word.lower().strip()
    sentence_lower = sentence.lower()
    pattern = r'\b' + re.escape(word_lower) + r'\b'

    if not re.search(pattern, sentence_lower):
        errors.append(f"Word '{word}' not found")

    # Check capitalization and punctuation
    if not sentence[0].isupper():
        errors.append("No capital letter at start")

    if sentence[-1] not in '.!?':
        errors.append("No punctuation at end")

    return errors

def apply_sentences(json_file, csv_file):
    """Apply sentences from JSON to CSV file."""

    # Load sentences
    with open(json_file, 'r', encoding='utf-8') as f:
        sentences_data = json.load(f)

    # Read CSV
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    # Ensure header has sentence columns
    if len(header) == 2:
        header.extend(['Sentence 1', 'Sentence 2', 'Sentence 3'])

    # Validate and apply sentences
    total_sentences = 0
    total_errors = 0

    print(f"Applying {len(sentences_data)} entries...\n")

    for item in sentences_data:
        row_num = item['row_num']
        word = item['word']
        sentences = item['sentences']

        # Convert row_num to 0-based index
        # row_num is Read tool's 1-based line number
        # rows[0] is the first data row (line 2 in Read tool, line 1 in Python)
        # So: row_idx = row_num - 2
        row_idx = row_num - 2

        # Ensure row has enough columns
        while len(rows[row_idx]) < 5:
            rows[row_idx].append('')

        # Validate each sentence
        for i, sentence in enumerate(sentences, 1):
            errors = validate_sentence(sentence, word)

            if errors:
                print(f"⚠ Row {row_num}, Word '{word}', Sentence {i}:")
                print(f"   \"{sentence}\"")
                for error in errors:
                    print(f"   - {error}")
                total_errors += 1
            else:
                total_sentences += 1

        # Apply to row
        rows[row_idx][2] = sentences[0]
        rows[row_idx][3] = sentences[1]
        rows[row_idx][4] = sentences[2]

    # Write back
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"\n{'='*60}")
    print(f"Results:")
    print(f"  Rows updated: {len(sentences_data)}")
    print(f"  Total sentences: {len(sentences_data) * 3}")
    print(f"  Valid sentences: {total_sentences}")
    print(f"  Sentences with issues: {total_errors}")
    print(f"{'='*60}")

    return total_errors == 0

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "batch_001_sentences.json"
    csv_file = "Task for LLM - MyEnglishWords.csv"

    success = apply_sentences(json_file, csv_file)
    sys.exit(0 if success else 1)
