class TextChunkerService:

    def split_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> list[str]:

        words = text.split()

        chunks: list[str] = []

        current_chunk: list[str] = []
        current_length = 0

        for word in words:

            word_length = len(word) + 1

            if current_length + word_length > chunk_size:

                chunks.append(
                    " ".join(current_chunk)
                )

                overlap_words = []

                overlap_length = 0

                for previous_word in reversed(current_chunk):

                    overlap_words.insert(0, previous_word)

                    overlap_length += len(previous_word) + 1

                    if overlap_length >= overlap:
                        break

                current_chunk = overlap_words
                current_length = overlap_length

            current_chunk.append(word)
            current_length += word_length

        if current_chunk:

            chunks.append(
                " ".join(current_chunk)
            )

        return chunks