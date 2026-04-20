# apps/companies/services.py
"""
Service d'envoi d'email via Resend.
Utilisé pour l'envoi du lien de première connexion à l'Admin d'une company.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _send(to: str, subject: str, html_body: str) -> bool:
    """
    Envoie un email via l'API Resend.
    Retourne True si succès, False sinon sans lever d'exception.
    """
    payload = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html_body,
    }
    headers = {
        "Authorization": f"Bearer {settings.RESEND_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(RESEND_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"[Email] Envoyé à {to} — sujet : {subject}")
        return True
    except Exception as exc:
        logger.error(f"[Email] Échec envoi à {to} : {exc}")
        return False


def send_first_login_email(user, company) -> bool:
    """
    Envoie le lien de première connexion à l'Admin nouvellement créé.

    Le lien contient le token UUID stocké sur l'utilisateur.
    Ce token est à usage unique — il devient inutilisable après
    que l'Admin a défini son mot de passe.

    Args:
        user    : instance CustomUser (role=admin)
        company : instance Company
    """
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    first_login_url = f"{frontend_url}/auth/first-login?token={user.first_login_token}"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px;
                 margin: 0 auto; padding: 20px; color: #333;">

      <div style="background: #fff; border-radius: 12px; padding: 32px;
                  box-shadow: 0 2px 8px rgba(0,0,0,0.07);">

        <h2 style="color: #1a1a2e; margin-bottom: 4px;">
          Bienvenue sur Gestion Intégrée Multi-Sites
        </h2>
        <p style="color: #666; font-size: 13px; margin-top: 0;">
          Votre entreprise a été créée avec succès sur la plateforme.
        </p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">

        <p>Bonjour,</p>
        <p>
          L'entreprise <strong>{company.name}</strong> vient d'être enregistrée
          sur la plateforme. Vous êtes désigné(e) comme administrateur(trice).
        </p>

        <div style="background: #f4f4f8; border-radius: 8px;
                    padding: 16px; margin: 20px 0;">
          <p style="margin: 0 0 6px; font-size: 13px; color: #888;">
            Votre email de connexion
          </p>
          <p style="margin: 0; font-size: 15px;">
            <code style="background: #e8e8f0; padding: 2px 8px; border-radius: 4px;">
              {user.email}
            </code>
          </p>
        </div>

        <p>
          Cliquez sur le bouton ci-dessous pour définir votre mot de passe
          et accéder à votre espace.
          <strong>Ce lien ne peut être utilisé qu'une seule fois.</strong>
        </p>

        <div style="text-align: center; margin: 32px 0;">
          <a href="{first_login_url}"
             style="background-color: #4f46e5; color: white; padding: 14px 32px;
                    text-decoration: none; border-radius: 8px; font-weight: bold;
                    display: inline-block; font-size: 15px;">
            Accéder à mon espace →
          </a>
        </div>

        <p style="color: #666; font-size: 13px;">
          Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
          <a href="{first_login_url}" style="color: #4f46e5; word-break: break-all;">
            {first_login_url}
          </a>
        </p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">

        <p style="color: #999; font-size: 12px; margin: 0;">
          Si vous n'êtes pas concerné(e) par cet email, ignorez-le.<br>
          Gestion Intégrée Multi-Sites — Conakry, Guinée
        </p>

      </div>
    </body>
    </html>
    """

    return _send(
        to=user.email,
        subject=f"Bienvenue sur la plateforme — {company.name}",
        html_body=html_body,
    )