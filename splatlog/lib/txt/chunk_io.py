from io import TextIOBase

from splatlog.lib.collections import iter_flat

type Chunks = list[str | Chunks]
type FmtOut = str


class ChunkIO(TextIOBase):
    chunks: Chunks

    def __init__(self):
        self.chunks = []

    def write(self, s: str, /) -> int:
        self.chunks.append(s)
        return len(s)

    def writable(self) -> bool:
        return True

    def getvalue(self) -> FmtOut:
        return "".join(iter_flat(self.chunks))
