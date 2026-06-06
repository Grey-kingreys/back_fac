# apps/companies/services.py
"""
Service d'envoi d'email via Resend.
Utilisé pour l'envoi du lien de première connexion à l'Admin d'une company.
"""

import logging

from django.conf import settings

import requests


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
    first_login_url = f"{frontend_url}/first-login?token={user.first_login_token}"
    full_name = f"{user.first_name} {user.last_name}".strip() or user.email

    html_body = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background-color:#f0fdf4; font-family: Arial, sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0fdf4; padding: 40px 20px;">
        <tr>
          <td align="center">
            <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:16px; overflow:hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.08); max-width:600px; width:100%;">

              <!-- Header -->
              <tr>
                <td style="background: linear-gradient(135deg, #2563eb 0%, #10b981 100%); padding: 32px 40px; text-align: center;">
                  <h1 style="margin:0; color:#ffffff; font-size:28px; font-weight:bold; letter-spacing:-0.5px;">
                    Djoula<span style="opacity:0.85;">Gest</span>
                  </h1>
                  <p style="margin:4px 0 0; color:rgba(255,255,255,0.8); font-size:13px;">
                    Gestion intégrée multi-sites
                  </p>
                </td>
              </tr>

              <!-- Body -->
              <tr>
                <td style="padding: 40px;">
                  <h2 style="margin:0 0 8px; color:#111827; font-size:22px;">
                    Bienvenue sur DjoulaGest !
                  </h2>
                  <p style="margin:0 0 24px; color:#6b7280; font-size:14px;">
                    Bonjour <strong style="color:#111827;">{full_name}</strong>,
                  </p>
                  <p style="color:#374151; font-size:15px; line-height:1.6; margin:0 0 16px;">
                    L'entreprise <strong>{company.name}</strong> vient d'être enregistrée sur <strong>DjoulaGest</strong>.
                    Vous avez été désigné(e) comme administrateur(trice) de cet espace.
                  </p>

                  <!-- Email box -->
                  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; margin:0 0 20px;">
                    <tr>
                      <td style="padding:16px 20px;">
                        <p style="margin:0 0 4px; font-size:12px; color:#9ca3af; text-transform:uppercase; letter-spacing:0.5px;">
                          Votre email de connexion
                        </p>
                        <p style="margin:0; font-size:15px; color:#111827; font-weight:bold;">
                          {user.email}
                        </p>
                      </td>
                    </tr>
                  </table>

                  <!-- Info box -->
                  <table width="100%" cellpadding="0" cellspacing="0" style="background:#eff6ff; border-left: 4px solid #2563eb; border-radius:0 8px 8px 0; margin:0 0 28px;">
                    <tr>
                      <td style="padding:14px 16px; color:#1d4ed8; font-size:13px;">
                        🔒 Ce lien d'activation est à <strong>usage unique</strong>. Il vous permettra de définir votre mot de passe.
                      </td>
                    </tr>
                  </table>

                  <!-- CTA Button -->
                  <div style="text-align:center; margin: 32px 0;">
                    <a href="{first_login_url}"
                       style="background: linear-gradient(135deg, #2563eb 0%, #10b981 100%);
                              color:#ffffff; padding:14px 36px; text-decoration:none;
                              border-radius:8px; font-weight:bold; font-size:15px;
                              display:inline-block; letter-spacing:0.3px;">
                      Accéder à mon espace →
                    </a>
                  </div>

                  <!-- Fallback link -->
                  <p style="color:#9ca3af; font-size:12px; text-align:center; margin:0 0 8px;">
                    Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :
                  </p>
                  <p style="text-align:center; margin:0 0 32px;">
                    <a href="{first_login_url}" style="color:#2563eb; font-size:12px; word-break:break-all;">{first_login_url}</a>
                  </p>

                  <hr style="border:none; border-top:1px solid #f3f4f6; margin:0 0 24px;">

                  <p style="color:#9ca3af; font-size:12px; line-height:1.6; margin:0;">
                    Si vous n'êtes pas concerné(e) par cet email, ignorez-le.
                    Aucune action ne sera prise de votre côté.
                  </p>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="background:#f9fafb; padding:20px 40px; text-align:center; border-top:1px solid #f3f4f6;">
                  <p style="margin:0; color:#9ca3af; font-size:12px;">
                    © 2025 <strong>DjoulaGest</strong> — Gestion intégrée multi-sites
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    return _send(
        to=user.email,
        subject=f"DjoulaGest — Activez votre compte {company.name}",
        html_body=html_body,
    )
