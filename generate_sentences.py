#!/usr/bin/env python3
"""
Generate educational English sentences for vocabulary words.
Processes vocabulary list in batches with quality control.
"""

import csv
import os
import sys
import time
import re
from typing import List, Dict, Tuple
import anthropic

# Configuration
BATCH_SIZE = 100
INPUT_FILE = "Task for LLM - MyEnglishWords.csv"
OUTPUT_FILE = "Task for LLM - MyEnglishWords.csv"
CHECKPOINT_FILE = "checkpoint.txt"

# CEFR level descriptions for context
LEVEL_DESCRIPTIONS = {
    "A1": "Beginner level - simple everyday expressions and basic phrases",
    "A2": "Elementary level - sentences about familiar topics and immediate needs",
    "B1": "Intermediate level - clear standard language on familiar matters",
    "B2": "Upper intermediate - detailed text on wide range of subjects",
    "C1": "Advanced - complex texts with implicit meaning",
    "C2": "Proficiency - sophisticated, nuanced expression"
}


def get_anthropic_client():
    """Initialize Anthropic client with API key from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def count_words(sentence: str) -> int:
    """Count words in a sentence."""
    # Remove punctuation and split
    words = re.findall(r'\b\w+\b', sentence)
    return len(words)


def validate_sentence(sentence: str, word: str, min_words: int = 4, max_words: int = 13) -> Tuple[bool, str]:
    """
    Validate a sentence meets all requirements.
    Returns (is_valid, error_message)
    """
    # Check word count
    word_count = count_words(sentence)
    if word_count < min_words or word_count > max_words:
        return False, f"Word count {word_count} not in range 4-13"

    # Check if exact word is present (case-insensitive)
    word_lower = word.lower().strip()
    sentence_lower = sentence.lower()

    # Check for word as a whole word (not part of another word)
    pattern = r'\b' + re.escape(word_lower) + r'\b'
    if not re.search(pattern, sentence_lower):
        return False, f"Word '{word}' not found in sentence"

    # Check sentence starts with capital and ends with punctuation
    if not sentence[0].isupper():
        return False, "Sentence doesn't start with capital letter"

    if sentence[-1] not in '.!?':
        return False, "Sentence doesn't end with punctuation"

    return True, ""


def generate_sentences(client: anthropic.Anthropic, word: str, level: str) -> List[str]:
    """
    Generate 3 educational sentences for a word using Claude API.
    """
    level_desc = LEVEL_DESCRIPTIONS.get(level, "intermediate level")

    prompt = f"""Generate exactly 3 educational English sentences for English learners.

Word: "{word}"
CEFR Level: {level} ({level_desc})

Requirements for each sentence:
1. Must contain exactly 4-13 words
2. Must include the exact word "{word}"
3. Must be appropriate for {level} level learners
4. Each sentence must be significantly different from the others (different context, meaning, grammar structure)
5. Must be grammatically correct and natural
6. Must provide strong educational value (show common usage, collocations, or important context)
7. Must start with a capital letter and end with proper punctuation

Output format: Return ONLY the 3 sentences, each on a separate line, numbered 1., 2., 3.
Do not include any other text or explanations."""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            temperature=0.8,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        response_text = message.content[0].text.strip()
        lines = response_text.split('\n')

        sentences = []
        for line in lines:
            line = line.strip()
            # Remove numbering like "1.", "2.", "3."
            if re.match(r'^\d+\.?\s*', line):
                line = re.sub(r'^\d+\.?\s*', '', line)
            if line:
                sentences.append(line)

        return sentences[:3]  # Ensure we only get 3 sentences

    except Exception as e:
        print(f"Error generating sentences for '{word}': {e}")
        return []


def check_sentence_quality(sentences: List[str], word: str, level: str) -> Tuple[bool, List[str]]:
    """
    Check quality of generated sentences.
    Returns (all_valid, list_of_errors)
    """
    errors = []

    if len(sentences) != 3:
        errors.append(f"Expected 3 sentences, got {len(sentences)}")
        return False, errors

    for i, sentence in enumerate(sentences, 1):
        is_valid, error = validate_sentence(sentence, word)
        if not is_valid:
            errors.append(f"Sentence {i}: {error} - '{sentence}'")

    # Check sentences are different enough
    if len(sentences) == 3:
        s1, s2, s3 = [s.lower() for s in sentences]
        # Simple check: sentences shouldn't be too similar
        if s1 == s2 or s2 == s3 or s1 == s3:
            errors.append("Sentences are too similar or identical")

    return len(errors) == 0, errors


def load_checkpoint() -> int:
    """Load the last processed row number from checkpoint file."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return int(f.read().strip())
    return 0


def save_checkpoint(row_num: int):
    """Save the current progress to checkpoint file."""
    with open(CHECKPOINT_FILE, 'w') as f:
        f.write(str(row_num))


def process_vocabulary_file():
    """Main processing function."""
    client = get_anthropic_client()

    # Read entire CSV file
    print(f"Reading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    total_rows = len(rows)
    print(f"Total vocabulary words: {total_rows}")

    # Add sentence columns to header if not present
    if len(header) == 2:
        header.extend(['Sentence 1', 'Sentence 2', 'Sentence 3'])

    # Load checkpoint
    start_row = load_checkpoint()
    if start_row > 0:
        print(f"Resuming from row {start_row + 1}/{total_rows}")

    # Process in batches
    batch_num = start_row // BATCH_SIZE
    quality_issues = []

    for batch_start in range(start_row, total_rows, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_rows)
        batch_num += 1

        print(f"\n{'='*60}")
        print(f"Processing Batch {batch_num}: Rows {batch_start + 1}-{batch_end} of {total_rows}")
        print(f"{'='*60}")

        batch_errors = []

        for i in range(batch_start, batch_end):
            row = rows[i]
            word = row[0].strip()
            level = row[1].strip() if len(row) > 1 else "A1"

            # Skip if already has sentences
            if len(row) >= 5 and row[2] and row[3] and row[4]:
                print(f"  [{i+1}/{total_rows}] Skipping '{word}' - already has sentences")
                continue

            print(f"  [{i+1}/{total_rows}] Generating for '{word}' ({level})...", end=' ')

            # Generate sentences with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                sentences = generate_sentences(client, word, level)

                if len(sentences) == 3:
                    # Validate quality
                    is_valid, errors = check_sentence_quality(sentences, word, level)

                    if is_valid:
                        # Extend row to have 5 columns
                        while len(row) < 5:
                            row.append('')

                        row[2] = sentences[0]
                        row[3] = sentences[1]
                        row[4] = sentences[2]

                        print("✓")
                        break
                    else:
                        if attempt < max_retries - 1:
                            print(f"⚠ (retry {attempt + 1}/{max_retries})", end=' ')
                            batch_errors.append(f"Row {i+1} '{word}': {'; '.join(errors)}")
                            time.sleep(1)
                        else:
                            print("✗")
                            batch_errors.append(f"Row {i+1} '{word}': Failed after {max_retries} attempts")
                else:
                    if attempt < max_retries - 1:
                        print(f"⚠ (retry {attempt + 1}/{max_retries})", end=' ')
                        time.sleep(1)
                    else:
                        print("✗")
                        batch_errors.append(f"Row {i+1} '{word}': Could not generate 3 sentences")

            # Small delay to avoid rate limiting
            time.sleep(0.3)

            # Save progress every 10 rows
            if (i + 1) % 10 == 0:
                save_checkpoint(i + 1)

        # Save after each batch
        print(f"\nSaving batch {batch_num}...")
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        save_checkpoint(batch_end)

        # Quality check for batch
        print(f"\n--- Batch {batch_num} Quality Report ---")
        if batch_errors:
            print(f"⚠ Issues found: {len(batch_errors)}")
            for error in batch_errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(batch_errors) > 10:
                print(f"  ... and {len(batch_errors) - 10} more")
            quality_issues.extend(batch_errors)
        else:
            print("✓ All sentences passed quality checks")

        print(f"Progress: {batch_end}/{total_rows} ({100*batch_end/total_rows:.1f}%)")

    # Final summary
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Total rows processed: {total_rows}")
    print(f"Total quality issues: {len(quality_issues)}")

    if quality_issues:
        print("\nRows with quality issues may need manual review.")

    # Clean up checkpoint file
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    print(f"\nOutput saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        process_vocabulary_file()
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
        print("Progress has been saved. Run the script again to resume.")
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
