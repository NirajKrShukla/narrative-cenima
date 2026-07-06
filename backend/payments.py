"""Pricing + Stripe payments logic for Story-to-Film paywall."""
from __future__ import annotations
import os
import math
from pathlib import Path
from typing import Optional

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CheckoutStatusResponse,
)

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))
FREE_TIER_MAX_BYTES = int(os.getenv("FREE_TIER_MAX_BYTES", "20971520"))  # 20 MB
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")


def get_film_size_bytes(final_film: Optional[str]) -> int:
    if not final_film:
        return 0
    path = STORAGE_DIR / final_film
    if not path.exists():
        return 0
    return path.stat().st_size


def compute_price_inr(project: dict) -> float:
    """Server-side pricing formula.

    price = ceil( (base 10 + 2 * MB above 20MB + 5 per Sora2 scene) * 1.10 ), min 19 INR.
    All values are INR floats (Stripe requires float).
    """
    scenes = project.get("scenes") or []
    # Count Sora 2 clips (those whose video_file does NOT end with _kb.mp4)
    sora_scenes = 0
    for s in scenes:
        vf = s.get("video_file") or ""
        if vf and not vf.endswith("_kb.mp4"):
            sora_scenes += 1

    size_bytes = get_film_size_bytes(project.get("final_film"))
    mb = size_bytes / (1024 * 1024)
    over_mb = max(0.0, mb - 20.0)

    base = 10.0
    size_fee = 2.0 * over_mb
    quality_fee = 5.0 * sora_scenes
    subtotal = base + size_fee + quality_fee
    total = math.ceil(subtotal * 1.10)  # 10% creator margin
    # Stripe INR minimum is roughly $0.50 USD (~₹45). Floor at ₹49 to keep checkout valid.
    total = max(total, 49)
    return float(total)


def compute_price_breakdown(project: dict) -> dict:
    scenes = project.get("scenes") or []
    sora_scenes = sum(1 for s in scenes if (s.get("video_file") or "") and not s.get("video_file", "").endswith("_kb.mp4"))
    size_bytes = get_film_size_bytes(project.get("final_film"))
    mb = round(size_bytes / (1024 * 1024), 2)
    over_mb = max(0.0, mb - 20.0)
    subtotal = 10.0 + 2.0 * over_mb + 5.0 * sora_scenes
    total = math.ceil(subtotal * 1.10)
    total = max(total, 49)
    return {
        "size_mb": mb,
        "over_free_mb": round(over_mb, 2),
        "sora_scenes": sora_scenes,
        "base_inr": 10.0,
        "size_fee_inr": round(2.0 * over_mb, 2),
        "quality_fee_inr": round(5.0 * sora_scenes, 2),
        "creator_margin_percent": 10,
        "total_inr": float(total),
        "free_tier_bytes": FREE_TIER_MAX_BYTES,
    }


def get_stripe(webhook_host_url: str) -> StripeCheckout:
    key = STRIPE_API_KEY or "sk_test_emergent"
    webhook_url = f"{webhook_host_url.rstrip('/')}/api/webhook/stripe"
    return StripeCheckout(api_key=key, webhook_url=webhook_url)


async def create_checkout(
    webhook_host_url: str,
    amount_inr: float,
    project_id: str,
    user_id: str,
    success_url: str,
    cancel_url: str,
) -> CheckoutSessionResponse:
    stripe = get_stripe(webhook_host_url)
    req = CheckoutSessionRequest(
        amount=float(amount_inr),
        currency="inr",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "project_id": project_id,
            "user_id": user_id,
            "purpose": "story_film_unlock",
        },
        # Stripe auto-enables UPI + Card when currency is INR on India-enabled accounts
        payment_methods=["card"],
    )
    return await stripe.create_checkout_session(req)


async def get_status(webhook_host_url: str, session_id: str) -> CheckoutStatusResponse:
    stripe = get_stripe(webhook_host_url)
    return await stripe.get_checkout_status(session_id)


async def handle_webhook(webhook_host_url: str, body: bytes, signature: str | None):
    stripe = get_stripe(webhook_host_url)
    return await stripe.handle_webhook(body, signature)
