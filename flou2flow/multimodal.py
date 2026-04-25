import base64
import io
import logging
import os
import tempfile
from typing import List

import fitz  # PyMuPDF
import whisper
import torch

from .llm import llm_client
from .config import settings

logger = logging.getLogger(__name__)

class MultimodalProcessor:
    """Handles local processing of Voice, PDF, and Images."""

    def __init__(self):
        self._whisper_model = None

    def _get_whisper(self):
        """Lazy load whisper model on CPU."""
        if self._whisper_model is None:
            logger.info("Loading Whisper 'base' model on CPU...")
            # 'base' is ~140MB and very accurate on CPU
            self._whisper_model = whisper.load_model("base", device="cpu")
        return self._whisper_model

    async def process_pdf(self, pdf_base64: str, model: str | None = None) -> str:
        """Extract text from a PDF (optimized for speed)."""
        pdf_data = base64.b64decode(pdf_base64)
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        full_content = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                full_content.append(f"--- Page {page_num + 1} ---\n{text}")
                
        doc.close()
        return "\n\n".join(full_content)

    async def process_voice(self, voice_base64: str) -> str:
        """Transcribe audio data using local Whisper."""
        audio_data = base64.b64decode(voice_base64)
        
        # Whisper requires a file path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
            
        try:
            model = self._get_whisper()
            result = model.transcribe(tmp_path)
            return result["text"]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def process_image(self, image_base64: str, model: str | None = None) -> str:
        """Analyze a standalone image."""
        return await llm_client.vision_chat(
            prompt="Perform OCR and describe any process flows or diagrams in this image.",
            image_data=image_base64,
            model=model or settings.VISION_MODEL
        )

# Singleton
processor = MultimodalProcessor()
