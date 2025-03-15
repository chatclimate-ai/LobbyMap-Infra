import re
from typing import List



class LayoutChunking:
    def __init__(self, min_words: int = 10):
        """
        :param min_words: Threshold for the minimum number of words in a paragraph.
                          Paragraphs with fewer words will be merged with neighbors.
        """
        self.min_words = min_words

    def chunk(self, markdown_text: str) -> List[str]:
        """
        Chunks a markdown file using the following strategy:
        
        1. If the markdown contains tables, each table is extracted as its own chunk.
           The table blocks are then removed from the text.
        2. The remaining text is split by paragraphs (blocks separated by at least two newlines).
        3. Consecutive header paragraphs (lines starting with '#' followed by space)
           are concatenated to the first following non-header paragraph.
        4. Markdown lists are treated as a single paragraph. If a list contains only one item,
           it is merged with the previous paragraph when possible.
        5. If a paragraph is “short” (fewer than min_words):
            a. If it ends with a colon, it is merged with the next paragraph.
            b. Otherwise, it is merged with the previous paragraph.
        
        :param markdown_text: The markdown source text.
        :return: A list of text chunks.
        """
        # First, split the markdown into ordered chunks (tables and text) while preserving order.
        ordered_chunks = self._split_tables(markdown_text)
        
        processed_chunks = []
        for chunk in ordered_chunks:
            if chunk["type"] == "table":
                # Leave table chunks unchanged.
                processed_chunks.append(chunk["content"])
            else:
                # Process text chunks:
                paragraphs = self._split_into_paragraphs(chunk["content"])
                paragraphs = self._merge_headers(paragraphs)
                paragraphs = self._merge_lists(paragraphs)
                paragraphs = self._merge_short_paragraphs(paragraphs)
                processed_chunks.extend(paragraphs)
                
        return processed_chunks

    def _split_tables(self, markdown_text: str) -> List[dict]:
        """
        Splits the input into ordered chunks. When a table is detected, it is output as a separate chunk.
        All other text is grouped into text chunks.
        """
        lines = markdown_text.splitlines()
        ordered_chunks = []
        i = 0
        # A simple regex to detect a table “separator” line (e.g. | --- | --- |)
        table_sep_re = re.compile(r'^\s*\|?[\s:-]+\|[\s:-\|]*$')
        
        while i < len(lines):
            line = lines[i]
            # Check if this line might start a table:
            if "|" in line and (i + 1 < len(lines)) and table_sep_re.match(lines[i + 1]):
                # Flush any pending text lines as a text chunk.
                # (If the last chunk in ordered_chunks is a text chunk, we leave it in place.)
                table_lines = [line, lines[i+1]]
                i += 2
                # Continue to grab subsequent lines that appear to be part of the table.
                while i < len(lines) and ("|" in lines[i]):
                    table_lines.append(lines[i])
                    i += 1
                ordered_chunks.append({
                    "type": "table",
                    "content": "\n".join(table_lines).strip()
                })
            else:
                # Accumulate non-table lines until a table is encountered.
                text_lines = []
                while i < len(lines) and not (
                    "|" in lines[i] and (i + 1 < len(lines)) and table_sep_re.match(lines[i + 1])
                ):
                    text_lines.append(lines[i])
                    i += 1
                if text_lines:
                    ordered_chunks.append({
                        "type": "text",
                        "content": "\n".join(text_lines).strip()
                    })
        return ordered_chunks

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Splits text into paragraphs using two (or more) newlines as a separator.
        """
        paragraphs = re.split(r'\n\s*\n', text)
        # Remove extra whitespace and ignore empty paragraphs.
        return [p.strip() for p in paragraphs if p.strip()]

    def _merge_headers(self, paragraphs: List[str]) -> List[str]:
        """
        Detects header paragraphs (lines starting with '#' followed by a space)
        and concatenates them with the first subsequent non-header paragraph.
        """
        merged = []
        header_buffer = []
        header_re = re.compile(r'^\s*#+\s+')
        for p in paragraphs:
            if header_re.match(p):
                header_buffer.append(p)
            else:
                if header_buffer:
                    combined = " ".join(header_buffer) + "\n\n" + p
                    merged.append(combined)
                    header_buffer = []
                else:
                    merged.append(p)
        if header_buffer:
            # If headers remain without following text, add them as a chunk.
            merged.append(" ".join(header_buffer))
        return merged

    def _merge_lists(self, paragraphs: List[str]) -> List[str]:
        """
        Treats markdown lists as a single paragraph. If a list has only one item,
        it is merged with the previous paragraph if one exists.
        A list item is detected as a line starting with a bullet (-, *, +) or a numbered item.
        """
        list_item_re = re.compile(r'^\s*(?:[-*+]|(?:\d+\.))\s+')
        merged = []
        for p in paragraphs:
            lines = p.splitlines()
            # Identify lines that look like list items.
            list_lines = [line for line in lines if list_item_re.match(line)]
            if list_lines:
                # Join all lines into one paragraph.
                joined = " ".join(line.strip() for line in lines)
                if len(list_lines) == 1 and merged:
                    # If there is only one list item, merge it with the previous paragraph.
                    merged[-1] = merged[-1] + " " + joined
                else:
                    merged.append(joined)
            else:
                merged.append(p)
        return merged

    def _merge_short_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """
        For paragraphs shorter than the threshold (self.min_words):
          a. If the paragraph ends with ":", merge it with the next paragraph, unless the next paragraph starts with a title marker.
          b. If the paragraph is short, merge it with the previous paragraph.
        """
        # First pass: Merge paragraphs ending with a colon with the following paragraph.
        merged_forward = []
        i = 0
        while i < len(paragraphs):
            current = paragraphs[i]
            # While the current paragraph ends with ":" and there is a next paragraph...
            while current.rstrip().endswith(":") and i < len(paragraphs) - 1:
                next_paragraph = paragraphs[i + 1]
                # If the next paragraph starts with a title marker, do not merge.
                if next_paragraph.lstrip().startswith("#"):
                    break
                i += 1
                current = current + " " + paragraphs[i]
            merged_forward.append(current)
            i += 1

        # Second pass: Merge paragraphs that are short with the previous paragraph.
        merged = []
        for p in merged_forward:
            if merged and len(p.split()) < self.min_words:
                merged[-1] = merged[-1] + " " + p
            else:
                merged.append(p)
        return merged
