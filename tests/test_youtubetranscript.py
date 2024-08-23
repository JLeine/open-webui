import unittest
from typing import Callable, Any

from langchain_community.document_loaders import YoutubeLoader
from pydantic import BaseModel, Field
from open_webui_tools.youtubetranscript import Tools

class YoutubeTranscriptProviderTest(unittest.IsolatedAsyncioTestCase):
    async def assert_transcript_length(self, url: str, expected_length: int):
        tools = Tools();
        self.assertEqual(len(await Tools().get_youtube_transcript(url)), expected_length)

    async def assert_transcript_error(self, url: str):
        response = await Tools().get_youtube_transcript(url)
        self.assertTrue("Error" in response)

    async def test_get_youtube_transcript(self):
        url = "https://www.youtube.com/watch?v=zhWDdy_5v2w"
        await self.assert_transcript_length(url, 1384)

    async def test_get_youtube_transcript_with_invalid_url(self):
        invalid_url = "https://www.example.com/invalid"
        missing_url = "https://www.youtube.com/watch?v=zhWDdy_5v3w"
        rick_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        await self.assert_transcript_error(invalid_url)
        await self.assert_transcript_error(missing_url)
        await self.assert_transcript_error(rick_url)

    async def test_get_youtube_transcript_with_none_arg(self):
        await self.assert_transcript_error(None)
        await self.assert_transcript_error("")


if __name__ == "__main__":
    unittest.main()