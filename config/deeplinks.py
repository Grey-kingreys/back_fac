"""
Deep links Android (App Links) + redirections web de repli.

- /.well-known/assetlinks.json : prouve que l'app DjoulaGest possède les liens
  du domaine → Android ouvre l'app au lieu du navigateur.
- /first-login et /reset-password : si l'app n'est PAS installée, le navigateur
  arrive ici → on redirige vers le front web (FRONTEND_URL).
"""

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse


# Empreinte SHA-256 de la clé qui signe l'APK.
# ⚠️ Actuellement la clé DEBUG + package par défaut. À mettre à jour quand on
# passera à une clé de release et un package final (ex: com.djoulagest.app).
ASSETLINKS = [
    {
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "com.example.mobile",
            "sha256_cert_fingerprints": [
                "C3:DE:14:3C:69:6D:B3:A2:FE:46:1E:C6:31:3E:B7:C5:6E:45:20:AE:98:B5:1C:E7:73:2E:C1:60:9F:23:E1:8E"
            ],
        },
    }
]


def assetlinks(request):
    """Sert /.well-known/assetlinks.json (vérification App Links)."""
    return JsonResponse(ASSETLINKS, safe=False)


def _web_fallback(path):
    """App non installée → le navigateur atterrit ici → redirection vers le front web."""

    def view(request):
        base = settings.FRONTEND_URL.rstrip("/")
        qs = request.META.get("QUERY_STRING", "")
        return HttpResponseRedirect(f"{base}{path}" + (f"?{qs}" if qs else ""))

    return view


first_login_web = _web_fallback("/first-login")
reset_password_web = _web_fallback("/reset-password")
