import json
import os
import unittest

from dotenv import load_dotenv
from open_webui_tools.paperless import Tools

load_dotenv()


class PaperlessDocumentLoaderTest(unittest.IsolatedAsyncioTestCase):
    async def assert_document_response(self, documentTypeName: str, expected_documents: int):
        paperless_tool = Tools()
        paperless_tool.valves.PAPERLESS_URL = os.getenv("PAPERLESS_URL")
        paperless_tool.valves.PAPERLESS_TOKEN = os.getenv("PAPERLESS_API_KEY")
        TAG = os.getenv("PAPERLESS_TEST_TAG")
        CORRESPONDENT = os.getenv("PAPERLESS_TEST_CORRESPONDENT")
        YEAR = os.getenv("PAPERLESS_TEST_YEAR")
        MONTH = os.getenv("PAPERLESS_TEST_MONTH")
        documents = await paperless_tool.get_paperless_documents(documentTypeName, TAG, CORRESPONDENT,
                                                                 YEAR, MONTH)
        decoded_documents = json.loads(documents)
        self.assertEqual(expected_documents, len(decoded_documents))

    async def assert_paperless_error(self, documentTypeName: str):
        response = await Tools().get_paperless_documents(documentTypeName)
        self.assertTrue("Query returned 0" in response)

    async def test_get_documents(self):
        documentType = os.getenv("PAPERLESS_TEST_DOCUMENT_TYPE")
        await self.assert_document_response(documentType, 8)

    async def test_get_paperless_documents_with_invalid_documentTypeName(self):
        invalid_documentTypeName = "DoesNotExist"
        await self.assert_paperless_error(invalid_documentTypeName)


if __name__ == "__main__":
    unittest.main()
