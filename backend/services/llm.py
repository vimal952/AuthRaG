import time
import google.generativeai as genai
from config import settings

# --- Ollama (commented out) ---
# import httpx
# async def generate(prompt: str, system: str = "") -> tuple[str, float]:
#     payload = {
#         "model": settings.OLLAMA_MODEL,
#         "prompt": prompt,
#         "system": system,
#         "stream": False,
#         "options": {"temperature": 0.2, "num_predict": 1024},
#     }
#     start = time.time()
#     async with httpx.AsyncClient(timeout=120.0) as client:
#         resp = await client.post(f"{settings.OLLAMA_URL}/api/generate", json=payload)
#         resp.raise_for_status()
#     latency = round((time.time() - start) * 1000, 2)
#     return resp.json()["response"].strip(), latency


genai.configure(api_key=settings.GEMINI_API_KEY)


async def generate(prompt: str, system: str = "") -> tuple[str, float]:
    """Returns (response_text, latency_ms)."""
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system or None,
        generation_config={"temperature": 0.2, "max_output_tokens": 4096},
    )
    start = time.time()
    response = model.generate_content(prompt)
    latency = round((time.time() - start) * 1000, 2)
    return response.text.strip(), latency


async def check_health() -> bool:
    # --- Ollama health check (commented out) ---
    # try:
    #     async with httpx.AsyncClient(timeout=5.0) as client:
    #         r = await client.get(f"{settings.OLLAMA_URL}/api/tags")
    #         return r.status_code == 200
    # except Exception:
    #     return False

    return bool(settings.GEMINI_API_KEY)
