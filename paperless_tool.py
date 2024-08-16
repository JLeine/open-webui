"""
title: Tool to interact with paperless documents
author: Jonas Leine
funding_url: https://github.com/open-webui
version: 1.0.2
license: MIT
"""
import json
import os
import requests
import unittest
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from typing import Callable, Any
from typing import Iterator, Optional

load_dotenv()


class DocumentEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Document):
            return {"page_content": obj.page_content, "metadata": obj.metadata}
        return super().default(obj)


class PaperlessDocumentLoader(BaseLoader):
    """Paperless document loader that retrieves all documents of a specific type and optionally by day, month and year"""

    def __init__(self, documentTypeName: str, documentTagName: Optional[str] = '', url: Optional[str] = '',
                 token: Optional[str] = '', created_year: Optional[int] = None,
                 created_month: Optional[int] = None) -> None:
        """Initialize the loader with a document_type.

        Args:
            documentTypeName: The name of the document type to load.
            documentTagName: The name of the document TAG to load.
            url: The URL to load documents from (optional).
            token: The authorization token for API access (optional).
            created_year: The year the documents were created (optional).
            created_month: The month the documents were created (optional).
        """
        self.url = url if url else '/'
        # Ensuring the URL ends with a '/' and checking its length
        if len(self.url) > 0 and not self.url.endswith('/'):
            self.url += '/'
        self.url += "api/documents/"
        self.token = token if token else ''
        self.documentTypeName = documentTypeName
        self.documentTagName = documentTagName

        # Set to current year and month if not provided
        now = datetime.now()
        self.created_year = created_year if created_year is not None else now.year
        self.created_month = created_month if created_month is not None else now.month

    def lazy_load(self) -> Iterator[Document]:  # <-- Does not take any arguments
        """A lazy loader that requests all documents from paperless.
        """
        querystring = {"document_type__name__icontains": self.documentTypeName,
                       "tags__name__icontains": self.documentTagName, "created__month": self.created_month,
                       "created_year": self.created_year}

        headers = {"Authorization": f"Token {self.token}"}
        response = requests.get(self.url, headers=headers, params=querystring)

        if response.status_code == 200:
            data = response.json()

            for result in data['results']:
                # Include all keys and values in the metadata
                metadata = {"source": f"{self.url.replace('/api', '')}{result['id']}", **result
                            # Merge the result dictionary into metadata
                            }

                # Remove any keys with None values or list values from metadata
                metadata = {k: v for k, v in metadata.items() if v is not None and not isinstance(v, list)}

                yield Document(page_content=result["content"], metadata=metadata, )


class EventEmitter:
    def __init__(self, event_emitter: Callable[[dict], Any] = None):
        self.event_emitter = event_emitter

    async def progress_update(self, description):
        await self.emit(description)

    async def error_update(self, description):
        await self.emit(description, "error", True)

    async def success_update(self, description):
        await self.emit(description, "success", True)

    async def emit(self, description="Unknown State", status="in_progress", done=False):
        if self.event_emitter:
            await self.event_emitter(
                {"type": "status", "data": {"status": status, "description": description, "done": done, }, })


class Tools:
    class Valves(BaseModel):
        PAPERLESS_URL: str = Field(default="https://paperless.yourdomain.com/",
                                   description="The domain of your paperless service", )
        PAPERLESS_TOKEN: str = Field(default="", description="The token to read docs from paperless", )

    def __init__(self):
        self.valves = self.Valves()

    async def get_paperless_documents(self, documentTypeName: str, documentTagName: Optional[str] = None,
                                      created_year: Optional[int] = None, created_month: Optional[int] = None,
                                      __event_emitter__: Callable[[dict], Any] = None) -> str:
        """
        Search for paperless documents and retrieve the content of relevant documents.

        :param documentTypeName: The documentTypeName the user is looking for.
        :param documentTagName: The documentTagName the user is looking for.
        :param created_month: the month where the the documents were created as int. If he asks for June this value is then 6. If the user does not specifiy anything skip it.
        :param created_year: the year where the the documents were created as int. If the user does not specifiy anything skip it.
        :return: All documents as a JSON string or an error as a string
        """
        emitter = EventEmitter(__event_emitter__)

        try:
            await emitter.progress_update(f"Getting documents for {documentTypeName}")

            error_message = f"Error: Invalid documentTypeName: {documentTypeName}"
            loader = PaperlessDocumentLoader(documentTypeName=documentTypeName, documentTagName=documentTagName, url=self.valves.PAPERLESS_URL,
                                             token=self.valves.PAPERLESS_TOKEN, created_month=created_month,
                                             created_year=created_year)
            documents = loader.load();

            if len(documents) == 0:
                error_message = f"Query returned 0 for documentTypeName {documentTypeName} documentTag {documentTagName} month {created_month} year {created_year}"
                await emitter.error_update(error_message)
                return error_message

            encoded_documents = json.dumps(documents, cls=DocumentEncoder, ensure_ascii=False)
            decoded_documents = json.loads(encoded_documents)

            if __event_emitter__:
                for document in decoded_documents:
                    await __event_emitter__({"type": "citation", "data": {"document": [document["page_content"]],
                                                                          "metadata": [{"source": document["metadata"][
                                                                              "title"]}], "source": {
                            "name": document["metadata"]["source"]}, }, })

            await emitter.success_update(
                f"Received {len(decoded_documents)} documents for documentType {documentTypeName} documentTag {documentTagName} month {created_month} year {created_year}")
            return encoded_documents
        except Exception as e:
            error_message = f"Error: {str(e)}"
            await emitter.error_update(error_message)
            return error_message


class PaperlessDocumentLoaderTest(unittest.IsolatedAsyncioTestCase):
    async def assert_document_response(self, documentTypeName: str, expected_documents: int):
        paperless_tool = Tools()
        paperless_tool.valves.PAPERLESS_URL = os.getenv("PAPERLESS_URL")
        paperless_tool.valves.PAPERLESS_TOKEN = os.getenv("PAPERLESS_API_KEY")
        documents = await paperless_tool.get_paperless_documents(documentTypeName, "Supermarkt", 2024, 7)
        decoded_documents = json.loads(documents)
        self.assertEqual(len(decoded_documents), expected_documents)

    async def assert_paperless_error(self, documentTypeName: str):
        response = await Tools().get_paperless_documents(documentTypeName)
        self.assertTrue("Query returned 0" in response)

    async def test_get_documents(self):
        documentType = "Kassenbon"
        await self.assert_document_response(documentType, 11)

    async def test_get_paperless_documents_with_invalid_documentTypeName(self):
        invalid_documentTypeName = "DoesNotExist"
        await self.assert_paperless_error(invalid_documentTypeName)


if __name__ == '__main__':
    print("Running tests...")
    unittest.main()
