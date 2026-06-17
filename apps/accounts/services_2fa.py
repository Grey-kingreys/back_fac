"""
Services 2FA — TOTP (Authy/Google Authenticator) et code OTP par email.
"""

import base64
import io
import logging
import secrets
import uuid

from django.conf import settings
from django.core.cache import cache

import pyotp
import qrcode
import requests


logger = logging.getLogger(__name__)

TOTP_ISSUER = "DjoulaGest"

EMAIL_OTP_TTL = 600        # 10 minutes
EMAIL_OTP_PREFIX = "2fa_email:"

TEMP_TOKEN_TTL = 300       # 5 minutes
TEMP_TOKEN_PREFIX = "2fa_temp:"

SETUP_SECRET_PREFIX = "2fa_setup_secret:"
SETUP_SECRET_TTL = 600     # 10 minutes


# ── TOTP ──────────────────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    """Génère un secret base32 aléatoire pour l'utilisateur."""
    return pyotp.random_base32()


def get_totp_qr_base64(user, secret: str) -> str:
    """Retourne l'image QR code en data:image/png;base64,... pour l'app Authy."""
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name=TOTP_ISSUER)
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f"data:image/png;base64,{encoded}"


def verify_totp(secret: str, code: str) -> bool:
    """Vérifie un code TOTP. Accepte ±1 intervalle (30 s) pour décalage d'horloge."""
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ── Email OTP ─────────────────────────────────────────────────────────────────

def generate_email_otp() -> str:
    """Génère un code OTP numérique à 6 chiffres."""
    return str(secrets.randbelow(900000) + 100000)


def store_email_otp(user_id: int, code: str) -> None:
    """Stocke le code OTP en cache Redis (10 min)."""
    cache.set(f"{EMAIL_OTP_PREFIX}{user_id}", code, timeout=EMAIL_OTP_TTL)


def verify_email_otp(user_id: int, code: str) -> bool:
    """Vérifie le code OTP email. Supprime le code après utilisation (usage unique)."""
    stored = cache.get(f"{EMAIL_OTP_PREFIX}{user_id}")
    if stored is None or stored != str(code):
        return False
    cache.delete(f"{EMAIL_OTP_PREFIX}{user_id}")
    return True


def send_2fa_email(user, code: str) -> None:
    """Envoie le code OTP 2FA à l'utilisateur via Resend."""
    from apps.accounts.services import RESEND_API_URL  # évite import circulaire

    full_name = f"{user.first_name} {user.last_name}".strip() or user.email

    html_body = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f0fdf4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0fdf4;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.08);max-width:600px;width:100%;">
        <tr>
          <td style="background:linear-gradient(135deg,#2563eb 0%,#10b981 100%);padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:bold;">DjoulaGest</h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">Vérification en deux étapes</p>
          </td>
        </tr>
        <tr>
          <td style="padding:40px;">
            <h2 style="margin:0 0 8px;color:#111827;font-size:22px;">Code de vérification</h2>
            <p style="margin:0 0 24px;color:#6b7280;font-size:14px;">
              Bonjour <strong style="color:#111827;">{full_name}</strong>,
            </p>
            <p style="color:#374151;font-size:15px;line-height:1.6;margin:0 0 28px;">
              Votre code de vérification pour vous connecter à <strong>DjoulaGest</strong> est :
            </p>
            <div style="text-align:center;margin:0 0 28px;">
              <div style="display:inline-block;background:#f0fdf4;border:2px solid #10b981;border-radius:12px;padding:20px 40px;">
                <span style="font-size:36px;font-weight:bold;color:#065f46;letter-spacing:8px;font-family:monospace;">{code}</span>
              </div>
            </div>
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#eff6ff;border-left:4px solid #2563eb;border-radius:0 8px 8px 0;margin:0 0 28px;">
              <tr>
                <td style="padding:14px 16px;color:#1d4ed8;font-size:13px;">
                  ⏱ Ce code est valable <strong>10 minutes</strong> et ne peut être utilisé qu'<strong>une seule fois</strong>.
                </td>
              </tr>
            </table>
            <p style="color:#9ca3af;font-size:12px;line-height:1.6;margin:0;">
              Si vous n'avez pas tenté de vous connecter, ignorez cet email et sécurisez votre compte.
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f9fafb;padding:20px 40px;text-align:center;border-top:1px solid #f3f4f6;">
            <p style="margin:0;color:#9ca3af;font-size:12px;">© 2026 <strong>DjoulaGest</strong> — Gestion intégrée multi-sites</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    payload = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [user.email],
        "subject": f"DjoulaGest — Code de vérification : {code}",
        "html": html_body,
    }
    headers = {
        "Authorization": f"Bearer {settings.RESEND_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info(f"Code 2FA envoyé à {user.email}")
    except Exception as exc:
        logger.error(f"Échec envoi code 2FA à {user.email}: {exc}")


# ── Token temporaire (session 2FA en attente) ─────────────────────────────────

def create_temp_token(user_id: int, method: str) -> str:
    """Crée un token temporaire valable 5 min. Retourné au client pour la 2ème étape du login."""
    token = str(uuid.uuid4())
    cache.set(
        f"{TEMP_TOKEN_PREFIX}{token}",
        {"user_id": user_id, "method": method},
        timeout=TEMP_TOKEN_TTL,
    )
    return token


def resolve_temp_token(token: str) -> dict | None:
    """Résout un temp_token → {'user_id': int, 'method': str} ou None si expiré."""
    return cache.get(f"{TEMP_TOKEN_PREFIX}{token}")


def invalidate_temp_token(token: str) -> None:
    """Supprime un temp_token après utilisation."""
    cache.delete(f"{TEMP_TOKEN_PREFIX}{token}")


# ── Secret TOTP temporaire (pendant la configuration) ─────────────────────────

def store_setup_secret(user_id: int, secret: str) -> None:
    cache.set(f"{SETUP_SECRET_PREFIX}{user_id}", secret, timeout=SETUP_SECRET_TTL)


def get_setup_secret(user_id: int) -> str | None:
    return cache.get(f"{SETUP_SECRET_PREFIX}{user_id}")


def delete_setup_secret(user_id: int) -> None:
    cache.delete(f"{SETUP_SECRET_PREFIX}{user_id}")
