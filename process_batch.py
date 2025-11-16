#!/usr/bin/env python3
"""
Helper script to process vocabulary batches.
Reads specified batch and prepares for sentence generation.
"""

import csv
import sys
import json

def read_batch(input_file, start_row, batch_size):
    """Read a specific batch from the CSV file."""
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)

        all_rows = list(reader)
        batch = all_rows[start_row:start_row + batch_size]

        return header, batch, len(all_rows)

def update_csv_with_sentences(input_file, sentences_data):
    """
    Update CSV with generated sentences.
    sentences_data: list of dicts with 'row_num', 'word', 'level', 'sentences' (list of 3)
    """
    # Read current file
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    # Ensure header has sentence columns
    if len(header) == 2:
        header.extend(['Sentence 1', 'Sentence 2', 'Sentence 3'])

    # Update rows with sentences
    for item in sentences_data:
        row_num = item['row_num']
        sentences = item['sentences']

        # Ensure row has enough columns
        while len(rows[row_num]) < 5:
            rows[row_num].append('')

        rows[row_num][2] = sentences[0]
        rows[row_num][3] = sentences[1]
        rows[row_num][4] = sentences[2]

    # Write back to file
    with open(input_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Updated {len(sentences_data)} rows in {input_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python process_batch.py <start_row> [batch_size]")
        print("Example: python process_batch.py 0 100")
        sys.exit(1)

    input_file = "Task for LLM - MyEnglishWords.csv"
    start_row = int(sys.argv[1])
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    header, batch, total = read_batch(input_file, start_row, batch_size)

    print(f"Batch: rows {start_row}-{start_row + len(batch) - 1} of {total}")
    print(f"Words in this batch: {len(batch)}")
    print()

    # Output batch in JSON format for easy processing
    batch_data = []
    for i, row in enumerate(batch):
        word = row[0].strip()
        level = row[1].strip() if len(row) > 1 else "A1"
        batch_data.append({
            "row_num": start_row + i,
            "word": word,
            "level": level
        })

    print(json.dumps(batch_data, indent=2))

if __name__ == "__main__":
    main()
