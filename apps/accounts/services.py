"""
R1-B05 — Service d'envoi d'email via Resend
Variable d'environnement requise : RESEND_KEY
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def send_password_reset_email(user, token: str) -> None:
    """
    Envoie le lien de réinitialisation de mot de passe à l'utilisateur.

    Args:
        user: instance CustomUser
        token: UUID du token de réinitialisation (durée de validité : 1h)
    """
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    reset_link = f"{frontend_url}/auth/reset-password?token={token}"
    full_name = f"{user.first_name} {user.last_name}".strip() or user.email

    html_body = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
      <h2 style="color: #1a1a2e;">Réinitialisation de votre mot de passe</h2>
      <p>Bonjour <strong>{full_name}</strong>,</p>
      <p>Vous avez demandé la réinitialisation de votre mot de passe pour votre compte <strong>Gestion Intégrée Multi-Sites</strong>.</p>
      <p>Cliquez sur le bouton ci-dessous pour définir un nouveau mot de passe. Ce lien est valable <strong>1 heure</strong>.</p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{reset_link}"
           style="background-color: #4f46e5; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 8px; font-weight: bold;
                  display: inline-block;">
          Réinitialiser mon mot de passe
        </a>
      </div>
      <p style="color: #666; font-size: 13px;">
        Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
        <a href="{reset_link}" style="color: #4f46e5;">{reset_link}</a>
      </p>
      <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
      <p style="color: #999; font-size: 12px;">
        Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
        Votre mot de passe ne sera pas modifié.<br>
        Ce lien expirera automatiquement dans 1 heure.
      </p>
    </body>
    </html>
    """

    payload = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [user.email],
        "subject": "Réinitialisation de votre mot de passe",
        "html": html_body,
    }

    headers = {
        "Authorization": f"Bearer {settings.RESEND_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Email de réinitialisation envoyé à {user.email}")
    except Exception as exc:
        # On logue l'erreur mais on ne la propage pas (sécurité anti-énumération)
        logger.error(f"Échec envoi email réinitialisation à {user.email}: {exc}")
