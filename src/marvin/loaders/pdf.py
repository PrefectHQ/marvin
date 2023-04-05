from contextlib import asynccontextmanager
from tempfile import NamedTemporaryFile
from typing import List
from urllib.parse import urlparse

import httpx
import pypdf

from marvin.loaders.base import Loader
from marvin.models.documents import Document


async def download_pdf(url: str) -> bytes:
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
            raw_pdf_content = await download_pdf(file_path)
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
                Document(
                    text=page.extract_text(),
                    metadata={"source": self.file_path, "page": i},
                    order=i,
                )
                for i, page in enumerate(pdf_reader.pages)
            ]


if __name__ == "__main__":
    import asyncio

    async def main():
        remote_pdf_document = await PDFLoader(
            file_path="https://www.cs.cmu.edu/~jgc/publication/The_Use_MMR_Diversity_Based_LTMIR_1998.pdf"
        ).load()

        local_pdf_document = await PDFLoader(
            file_path="/Users/nate/Downloads/MMR.pdf"
        ).load()

        assert remote_pdf_document[0].text == local_pdf_document[0].text

    asyncio.run(main())
