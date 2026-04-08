"""LLM client helpers for alarm image analysis."""

import base64
import mimetypes
import re
from urllib.parse import urlparse

import requests
from openai import OpenAI

from config import LLM_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL, LLM_TIMEOUT_SEC


def _guess_mime_type(image_path):
    mime, _ = mimetypes.guess_type(image_path)
    return mime or "image/jpeg"


def _shorten_analysis_text(text, max_chars=20):
    """Normalize model output into a short single-line summary."""
    cleaned = re.sub(r"\s+", "", (text or "").strip())
    cleaned = re.sub(r"[。；;！!？?]+$", "", cleaned)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars]


def _is_bitexing_base_url(base_url):
    hostname = (urlparse(base_url).hostname or "").lower()
    return hostname.endswith("bitexingai.com")


def _build_alarm_prompt():
    return (
        "你是一名叉车作业安全分析助手。已知这是一张报警图片，"
        "报警原因固定为“行人离叉车过近”，且摄像头安装在叉车上。"
        "请只输出一句中文短语，20个字以内，概括行人为什么没有及时注意到叉车。"
        "优先概括为：低头作业、背对叉车、被货物遮挡、通道视线受阻、正在搬运等。"
        "如果证据不足，只输出“画面不足以判断”。"
        "不要解释，不要分点，不要标点，不要超过20个字。"
    )


def _extract_chat_completion_text(payload):
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "".join(parts).strip()
    return ""


def _analyze_with_bitexing_relay(data_url):
    if not OPENAI_BASE_URL:
        raise RuntimeError("OPENAI_BASE_URL is not set")

    url = OPENAI_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _build_alarm_prompt()},
                    {"type": "image_url", "image_url": data_url},
                ],
            }
        ],
        "stream": False,
        "max_tokens": 100,
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT_SEC)
    if response.status_code == 468:
        raise RuntimeError("Relay blocked image request (HTTP 468)")
    if response.status_code >= 400:
        raise RuntimeError(f"Relay request failed ({response.status_code}): {response.text[:300]}")

    payload = response.json()
    text = _extract_chat_completion_text(payload)
    if not text:
        raise RuntimeError("Empty response from relay chat completions")
    return _shorten_analysis_text(text)


def analyze_alarm_image(image_path):
    """
    Call the multimodal model to analyze why the pedestrian may not have
    noticed the forklift in an alarm image.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    mime = _guess_mime_type(image_path)
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"
    prompt = _build_alarm_prompt()

    if OPENAI_BASE_URL and _is_bitexing_base_url(OPENAI_BASE_URL):
        return _analyze_with_bitexing_relay(data_url)

    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL or None,
        timeout=LLM_TIMEOUT_SEC,
    )
    response = client.responses.create(
        model=LLM_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ],
            }
        ],
    )

    text = (response.output_text or "").strip()
    if not text:
        raise RuntimeError("Empty response from LLM")
    return _shorten_analysis_text(text)


def describe_image(image_path):
    """Backward-compatible alias for older callers."""
    return analyze_alarm_image(image_path)
