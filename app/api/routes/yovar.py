from __future__ import annotations
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/yovar", tags=["yovar"])
MISTRAL_KEY = os.getenv("MISTRAL_API_KEY", "RZih7gTFIi0NP4cZYbNpuMq4OIpkqmNG")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

class Message(BaseModel):
    role: str
    content: str

class YovarRequest(BaseModel):
    messages: List[Message]

@router.post("")
async def yovar_chat(payload: YovarRequest) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                MISTRAL_URL,
                headers={"Authorization": f"Bearer {MISTRAL_KEY}", "Content-Type": "application/json"},
                json={"model": "mistral-small-latest", "messages": [m.dict() for m in payload.messages], "max_tokens": 400, "temperature": 0.7},
            )
            data = resp.json()
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=data.get("message", "Mistral error"))
            return {"reply": data["choices"][0]["message"]["content"]}
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))
