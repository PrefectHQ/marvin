from contextlib import asynccontextmanager
from tempfile import NamedTemporaryFile
from typing import List
from urllib.parse import urlparse

import httpx

try:
    import pypdf
except ModuleNotFoundError:
    raise ImportError(
        "The PDF loader requires the pypdf package. "
        "Install it with `pip install 'marvin[loaders]'`."
    )

from marvin._rag.documents import Document, document_to_excerpts
from marvin._rag.loaders.base import Loader


async def download_url_content(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.content


def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)


class PDFLoader(Loader):
    file_path: str

    @asynccontextmanager
    async def open_pdf_file(self, file_path: str):
        if is_valid_url(file_path):
            raw_pdf_content = await download_url_content(file_path)
            with NamedTemporaryFile() as temp_file:
                temp_file.write(raw_pdf_content)
                temp_file.flush()
                yield temp_file
        else:
            with open(file_path, "rb") as pdf_file_obj:
                yield pdf_file_obj

    async def load(self) -> List[Document]:
        async with self.open_pdf_file(self.file_path) as pdf_file_obj:
            pdf_reader = pypdf.PdfReader(pdf_file_obj)
            return [
                document
                for i, page in enumerate(pdf_reader.pages)
                for document in document_to_excerpts(
                    Document(
                        text=page.extractText(),
                        metadata={"page": i + 1, "file_path": self.file_path},
                    )
                )
            ]
