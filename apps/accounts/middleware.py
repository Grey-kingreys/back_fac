"""
R1-B05 / R1-B09 — Middleware LoginLogMiddleware
Enregistre chaque tentative de connexion (succès et échecs) dans LoginLog.
Modèle LoginLog défini dans apps/accounts/models.py (R1-B09).

À ajouter dans config/settings.py :
    MIDDLEWARE = [
        ...
        "apps.accounts.middleware.LoginLogMiddleware",
    ]
"""

import json


class LoginLogMiddleware:
    """
    Intercepte les réponses sur /api/auth/login/ et enregistre le résultat
    dans LoginLog (succès si status 200, échec sinon).
    Ignoré silencieusement si LoginLog n'existe pas encore (avant R1-B09).
    """

    LOGIN_PATH = "/api/auth/login/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path == self.LOGIN_PATH and request.method == "POST":
            self._log_attempt(request, response)

        return response

    def _log_attempt(self, request, response):
        # LoginLog sera créé au ticket R1-B09 — on ignore si absent
        try:
            from .models import LoginLog
        except ImportError:
            return

        from django.contrib.auth import get_user_model
        User = get_user_model()

        success = response.status_code == 200
        user = None

        # Tentative de récupération de l'utilisateur
        try:
            body = json.loads(request.body.decode("utf-8"))
            email = body.get("email", "")
            user = User.objects.filter(email=email).first()
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        try:
            LoginLog.objects.create(
                user=user,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
                success=success,
            )
        except Exception:
            # Ne jamais bloquer la réponse à cause du log
            pass

    @staticmethod
    def _get_client_ip(request) -> str:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
