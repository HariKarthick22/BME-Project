"""
backend/services/ollama_service.py

Ollama integration for MedGemma 4B (medgemma:4b-it) — multimodal medical AI.
Runs locally via Ollama on http://localhost:11434.

Setup:
  ollama pull medgemma:4b-it      # one-time (~3GB Q4_K_M)
  ollama serve

Memory: ~3.5GB unified memory — safe on M2 8GB and HP 8GB laptops.
"""

import base64
import json
import logging
import io

import httpx

from ..config.prompts import SYSTEM_PROMPT, MEDICAL_DISCLAIMER

logger = logging.getLogger(__name__)

OLLAMA_BASE = "http://localhost:11434"
MEDGEMMA_MODEL = "dcarrascosa/medgemma-1.5-4b-it:Q4_K_M"
FALLBACK_MODEL = "llama3.2:3b"
TIMEOUT = 120  # MedGemma can take 30-90s on CPU


async def _available_models() -> list[str]:
    """Return list of pulled model names from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


async def _pick_model() -> str | None:
    """Return best available model name, or None if Ollama is down."""
    available = await _available_models()
    for candidate in (MEDGEMMA_MODEL, FALLBACK_MODEL):
        base = candidate.split(":")[0]
        if any(base in m for m in available):
            return candidate
    return None


async def chat_with_medgemma(
    messages: list[dict],
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    """
    Non-streaming chat with MedGemma via Ollama.

    Falls back to FALLBACK_MODEL or a stub string if Ollama is unavailable.

    Args:
        messages: [{"role": "user"|"assistant", "content": str}, ...]
        system_prompt: Injected before the conversation.

    Returns:
        Response text.
    """
    model = await _pick_model()
    if model is None:
        return (
            "CarePath AI: local model not loaded. "
            "Run: ollama pull medgemma:4b-it\n\n" + MEDICAL_DISCLAIMER
        )

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512, "num_ctx": 4096},
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
    except httpx.TimeoutException:
        raise TimeoutError("Model inference timed out. Try again.")
    except Exception as e:
        logger.error("Ollama chat error: %s", e)
        raise


async def stream_chat_with_medgemma(
    messages: list[dict],
    system_prompt: str = SYSTEM_PROMPT,
):
    """
    Async generator yielding streamed text chunks from MedGemma.

    Yields:
        str chunks as they arrive from the model.
    """
    model = await _pick_model()
    if model is None:
        yield "Local model not available. Run: ollama pull medgemma:4b-it"
        return

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "stream": True,
        "options": {"temperature": 0.3, "num_predict": 512, "num_ctx": 4096},
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream("POST", f"{OLLAMA_BASE}/api/chat", json=payload) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    text = chunk.get("message", {}).get("content", "")
                    if text:
                        yield text
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue


async def analyze_xray_image(image_bytes: bytes, filename: str = "xray.jpg") -> dict:
    """
    Analyze an X-ray image using MedGemma vision via Ollama.
    Falls back to a ViT classifier if MedGemma is unavailable.

    Returns:
        dict with summary, findings, disclaimer, model_used.
    """
    model = await _pick_model()
    if model and "medgemma" in model:
        return await _analyze_with_medgemma(image_bytes, model)
    logger.warning("MedGemma unavailable for X-ray — using ViT fallback")
    return await _analyze_xray_vit_fallback(image_bytes)


async def _analyze_with_medgemma(image_bytes: bytes, model: str) -> dict:
    """Send X-ray bytes to MedGemma as a base64-encoded image message."""
    b64 = base64.b64encode(image_bytes).decode()
    prompt = (
        "Describe key findings visible in this X-ray in 2-3 sentences. "
        "Do NOT provide a diagnosis. Describe observable findings only."
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [b64]}],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 256},
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            r.raise_for_status()
            findings = r.json()["message"]["content"]
    except Exception as e:
        logger.error("MedGemma X-ray failed: %s — falling back to ViT", e)
        return await _analyze_xray_vit_fallback(image_bytes)

    return {
        "summary": f"AI X-ray Analysis: {findings}{MEDICAL_DISCLAIMER}",
        "findings": findings,
        "disclaimer": MEDICAL_DISCLAIMER.strip(),
        "model_used": model,
    }


async def _analyze_xray_vit_fallback(image_bytes: bytes) -> dict:
    """
    ViT-based chest X-ray classifier fallback (CPU, ~200MB model).
    Uses nickmuchi/vit-finetuned-chest-xray-pneumonia.
    """
    try:
        from PIL import Image
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForImageClassification

        model_id = "nickmuchi/vit-finetuned-chest-xray-pneumonia"
        extractor = AutoFeatureExtractor.from_pretrained(model_id)
        clf_model = AutoModelForImageClassification.from_pretrained(model_id)
        clf_model.training = False  # inference mode

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = extractor(images=image, return_tensors="pt")

        with torch.inference_mode():
            logits = clf_model(**inputs).logits
            probs = torch.nn.functional.softmax(logits, dim=-1)[0]

        idx = int(probs.argmax())
        label = clf_model.config.id2label[idx]
        confidence = round(float(probs[idx]) * 100, 1)
        findings = f"Possible finding: {label} (confidence {confidence}%)"

    except Exception as e:
        logger.error("ViT fallback error: %s", e)
        findings = "Unable to analyze image automatically."

    return {
        "summary": f"AI X-ray Analysis: {findings}{MEDICAL_DISCLAIMER}",
        "findings": findings,
        "disclaimer": MEDICAL_DISCLAIMER.strip(),
        "model_used": "vit-chest-xray-fallback",
    }
