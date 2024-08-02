import os
import json
from ziman.models import WordDB
async def export_words():
    export_directory = "words"
    os.makedirs(export_directory, exist_ok=True)
    file_handlers = {}
    file_indices = {}
    words_per_file = 100
    word_counts = {}  # New dictionary to track word counts for each letter

    # Initialize Tortoise ORM
    # Get total count of words
    total_words = await WordDB.filter(is_confirmed=True).count()
    batch_size = 100

    for offset in range(0, total_words, batch_size):
        # Fetch words in batches
        words = (
            await WordDB.filter(is_confirmed=True)
            .prefetch_related(
                "created_by",
                "definitions__created_by",
                "definitions__sentences__created_by",
            )
            .order_by("updated_at")
            .offset(offset)
            .limit(batch_size)
        )

        for word in words:
            first_letter = word.content[0].lower()

            if first_letter not in word_counts:
                word_counts[first_letter] = 0

            if (
                word_counts[first_letter] % words_per_file == 0
                or first_letter not in file_handlers
            ):
                if first_letter in file_handlers:
                    file_handlers[first_letter].write("\n]")
                    file_handlers[first_letter].close()

                if first_letter not in file_indices:
                    file_indices[first_letter] = 1
                else:
                    file_indices[first_letter] += 1

                file_path = os.path.join(
                    export_directory,
                    f"words_{first_letter}_{file_indices[first_letter]}.json",
                )
                file_handlers[first_letter] = open(file_path, "w", encoding="utf-8")
                file_handlers[first_letter].write("[\n")

            fetched_word = {
                "author": {
                    "firstname": word.created_by.firstname,
                    "lastname": word.created_by.lastname,
                },
                "content": word.content,
                "definitions": [],
            }

            for db_word_definition in word.definitions:
                fetched_word["definitions"].append(
                    {
                        "content": db_word_definition.content,
                        "type": db_word_definition.type.value,
                        "author": {
                            "firstname": db_word_definition.created_by.firstname,
                            "lastname": db_word_definition.created_by.lastname,
                        },
                        "sentences": [
                            {
                                "content": sentence.content,
                                "tense": sentence.tense.value,
                                "word_form": sentence.word_form,
                                "author": {
                                    "firstname": sentence.created_by.firstname,
                                    "lastname": sentence.created_by.lastname,
                                },
                            }
                            for sentence in db_word_definition.sentences
                        ],
                    }
                )

            json.dump(
                fetched_word, file_handlers[first_letter], ensure_ascii=False, indent=2
            )
            file_handlers[first_letter].write(",\n")
            file_handlers[first_letter].flush()

            word_counts[first_letter] += 1  # Increment the word count for this letter

    for handler in file_handlers.values():
        handler.seek(handler.tell() - 2)  # Remove the last comma and newline
        handler.write("\n]")
        handler.close()

    print(
        f"Exported {total_words} words to separate files in the '{export_directory}' directory."
    )
