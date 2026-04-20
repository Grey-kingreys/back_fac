# apps/accounts/middleware.py
"""

1. AuditMiddleware  : injecte user + IP dans le thread-local d'audit
                      (utilisé par les signaux pour alimenter AuditLog)

2. LoginLogMiddleware : enregistre chaque tentative de connexion dans LoginLog
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilitaire commun
# ---------------------------------------------------------------------------

def _get_client_ip(request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ---------------------------------------------------------------------------
# 1. AuditMiddleware — thread-local pour les signaux
# ---------------------------------------------------------------------------

class AuditMiddleware:
    """
    Injecte l'utilisateur connecté et son IP dans le contexte thread-local.
    Les signaux Django (signals.py) lisent ce contexte pour remplir AuditLog.

    À placer APRÈS AuthenticationMiddleware dans MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Import différé pour éviter les imports circulaires au démarrage
        from .signals import set_audit_context, clear_audit_context

        user = getattr(request, 'user', None)
        if user and not user.is_authenticated:
            user = None

        set_audit_context(user=user, ip=_get_client_ip(request))
        try:
            response = self.get_response(request)
        finally:
            clear_audit_context()

        return response


# ---------------------------------------------------------------------------
# 2. LoginLogMiddleware — enregistre les tentatives de connexion
# ---------------------------------------------------------------------------

class LoginLogMiddleware:
    """
    Intercepte les réponses sur /api/auth/login/ et enregistre le résultat
    dans LoginLog (succès si status 200, échec sinon).

    Ignoré silencieusement si LoginLog n'existe pas encore.
    Compatibilité : fonctionne avec les deux systèmes de settings du projet.
    """

    LOGIN_PATH = '/api/auth/login/'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path == self.LOGIN_PATH and request.method == 'POST':
            self._log_attempt(request, response)

        return response

    def _log_attempt(self, request, response):
        try:
            from .audit_models import LoginLog
        except ImportError:
            return

        from django.contrib.auth import get_user_model
        User = get_user_model()

        success = response.status_code == 200
        user = None

        email = None

        try:
            if hasattr(request, 'data'):
                email = request.data.get('email')
        except Exception:
            pass

        if email:
            user = User.objects.filter(email=email).first()

        try:
            LoginLog.objects.create(
                user=user,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
                success=success,
            )
        except Exception as e:
            logger.warning(f'[LoginLog] Échec enregistrement : {e}')