"""
Synonym loader abstraction. Phase 1 uses file-based synonyms.
"""

from typing import List
from pathlib import Path


class SynonymLoader:
    def load_synonyms(self) -> List[str]:
        raise NotImplementedError


class FileSynonymLoader(SynonymLoader):
    def __init__(self, synonyms_path: Path):
        self.synonyms_path = synonyms_path

    def load_synonyms(self) -> List[str]:
        if not self.synonyms_path.exists():
            return []
        lines: List[str] = []
        with self.synonyms_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                lines.append(line)
        return lines



