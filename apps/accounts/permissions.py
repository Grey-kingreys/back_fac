"""
apps/accounts/permissions.py
Classes de permissions réutilisables pour l'isolation multi-companies.
"""

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import View

from .models import CustomUser, Role


class IsCompanyMember(permissions.BasePermission):
    """
    Vérifie que l'utilisateur appartient à la même company que la ressource.

    Utilisation :
    - Pour les vues de détail : vérifie que obj.company == request.user.company
    - Pour les vues de liste : doit être combiné avec CompanyFilterMixin
    """

    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """
        Vérifie l'accès à un objet spécifique.
        L'objet doit avoir un attribut 'company' ou 'get_company()'.
        Le superadmin n'a pas accès aux données métier internes — isolation SaaS §8.
        """
        user_company = request.user.company
        if not user_company:
            return False

        # Vérifier si l'objet a un attribut company direct
        if hasattr(obj, 'company'):
            return obj.company == user_company

        # Vérifier si l'objet a une méthode get_company()
        if hasattr(obj, 'get_company'):
            return obj.get_company() == user_company

        # Vérifier si l'objet lui-même est une company
        if hasattr(obj, 'id') and hasattr(user_company, 'id'):
            return obj.id == user_company.id

        return False


class HasRole(permissions.BasePermission):
    """
    Vérifie que l'utilisateur possède l'un des rôles autorisés.

    Pour usage dans permission_classes, utiliser la factory HasAnyRole :
        permission_classes = [HasAnyRole(Role.ADMIN, Role.SUPERVISEUR)]
    Pour vérification directe dans le code :
        HasRole([Role.ADMIN]).has_permission(request, view)
    """
    required_roles: list = []

    def __init__(self, allowed_roles=None):
        super().__init__()
        if allowed_roles is not None:
            self.required_roles = list(allowed_roles)

    def has_permission(self, request: Request, view: View) -> bool:
        """Vérifie le rôle de l'utilisateur."""
        if not request.user or not request.user.is_authenticated:
            return False

        if not self.required_roles:
            return True

        # Pas de bypass superadmin : il doit être explicitement dans required_roles
        # ou bloqué par IsSuperAdminBlocked sur les endpoints opérationnels.
        return request.user.role in self.required_roles


def HasAnyRole(*roles):
    """
    Factory retournant une CLASSE HasRole pour usage dans permission_classes.

    Usage :
        permission_classes = [HasAnyRole(Role.ADMIN, Role.SUPERVISEUR)]
    """
    return type("HasAnyRole", (HasRole,), {"required_roles": list(roles)})


class IsOwnerOrCompanyAdmin(permissions.BasePermission):
    """
    Permission pour les ressources personnelles :
    - L'utilisateur peut accéder à ses propres ressources
    - Les admins/superadmins peuvent accéder aux ressources de leur company
    """

    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """Vérifie l'accès à un objet spécifique."""
        user = request.user

        # L'utilisateur peut accéder à ses propres ressources
        if hasattr(obj, 'user') and obj.user == user:
            return True

        if hasattr(obj, 'id') and hasattr(user, 'id') and obj.id == user.id:
            return True

        # Les admins peuvent accéder aux ressources de leur company
        if user.is_admin_or_above and hasattr(obj, 'company'):
            return obj.company == user.company

        return False


# ── Isolation géographique par rôle (entreprise → zone → dépôt) ───────────────
# Périmètre par défaut (cahier des charges / skill gestion-multisites) :
#   admin → toute l'entreprise · superviseur → sa zone ·
#   gestionnaire_stock / caissier / commercial / chauffeur → leur dépôt ·
#   maintenancier → entreprise (la flotte n'a pas de dépôt).

DEPOT_SCOPE_ROLES = (
    Role.GESTIONNAIRE_STOCK,
    Role.CAISSIER,
    Role.COMMERCIAL,
    Role.CHAUFFEUR,
)


def geo_scope_level(user):
    """Niveau d'isolation géographique applicable à l'utilisateur selon son rôle."""
    if user.role == Role.ADMIN:
        return 'company'
    if user.role == Role.SUPERVISEUR:
        return 'zone'
    if user.role in DEPOT_SCOPE_ROLES:
        return 'depot'
    # maintenancier (flotte = entreprise) et tout autre rôle métier non géo-localisé
    return 'company'


def apply_geo_scope(queryset, user, *, depot_fields=None, zone_field=None):
    """
    Restreint un queryset (DÉJÀ filtré par company) au périmètre géographique de
    l'utilisateur selon son rôle.

    - `depot_fields` : chemin ORM (str) ou liste de chemins vers le Dépôt. Une
      liste produit un filtre OR (modèles à 2 dépôts : transfert, mission).
    - `zone_field`   : chemin ORM vers la Zone.

    Si la dimension du niveau du rôle est absente du modèle, on retombe sur la
    dimension disponible la plus proche ; sinon aucun filtre géographique
    (ressource sans dimension géo, ex. catalogue produits).
    """
    from django.db.models import Q

    level = geo_scope_level(user)
    if level == 'company':
        return queryset

    if isinstance(depot_fields, str):
        depot_fields = [depot_fields]

    # Ressource sans dimension géographique (ex. catalogue, zones, utilisateurs) :
    # aucun filtre dépôt/zone — l'utilisateur voit toute son entreprise.
    if not depot_fields and not zone_field:
        return queryset

    if level == 'zone':
        if not user.zone_id:
            return queryset.none()
        if zone_field:
            return queryset.filter(**{zone_field: user.zone_id})
        q = Q()
        for f in depot_fields:
            q |= Q(**{f + '__zone': user.zone_id})
        return queryset.filter(q)

    # level == 'depot'
    if not user.depot_id:
        return queryset.none()
    if depot_fields:
        q = Q()
        for f in depot_fields:
            q |= Q(**{f: user.depot_id})
        return queryset.filter(q)
    # rôle dépôt sur une ressource zone-only → limité à la zone de son dépôt
    return queryset.filter(**{zone_field: user.depot.zone_id})


def depot_in_scope(user, depot):
    """Retourne True si `depot` est dans le périmètre de l'utilisateur (sans lever d'exception)."""
    if depot is None:
        return True
    level = geo_scope_level(user)
    if level == 'company':
        return getattr(depot.zone, 'company_id', None) == user.company_id
    if level == 'zone':
        return depot.zone_id == user.zone_id
    # level == 'depot'
    return depot.id == user.depot_id


def assert_depot_in_scope(user, depot):
    """Lève PermissionDenied si `depot` est hors du périmètre d'écriture de l'utilisateur."""
    from rest_framework.exceptions import PermissionDenied

    if depot is None:
        return
    level = geo_scope_level(user)
    if level == 'company':
        if getattr(depot.zone, 'company_id', None) != user.company_id:
            raise PermissionDenied("Ce dépôt n'appartient pas à votre entreprise.")
        return
    if level == 'zone':
        if depot.zone_id != user.zone_id:
            raise PermissionDenied("Action interdite : ce dépôt est hors de votre zone.")
        return
    # level == 'depot'
    if depot.id != user.depot_id:
        raise PermissionDenied("Action interdite : ce dépôt n'est pas le vôtre.")


def assert_zone_in_scope(user, zone):
    """Lève PermissionDenied si `zone` est hors du périmètre d'écriture de l'utilisateur."""
    from rest_framework.exceptions import PermissionDenied

    if zone is None:
        return
    level = geo_scope_level(user)
    if level == 'company':
        if zone.company_id != user.company_id:
            raise PermissionDenied("Cette zone n'appartient pas à votre entreprise.")
        return
    if level == 'zone':
        if zone.id != user.zone_id:
            raise PermissionDenied("Action interdite : zone hors de votre périmètre.")
        return
    # level == 'depot' : autorisé seulement sur la zone de son propre dépôt
    if not (user.depot_id and user.depot.zone_id == zone.id):
        raise PermissionDenied("Action interdite : zone hors de votre périmètre.")


class CompanyFilterMixin:
    """
    Mixin pour filtrer automatiquement les QuerySets par company puis par
    périmètre géographique du rôle (zone pour le superviseur, dépôt pour les
    rôles dépôt — voir geo_scope_level / apply_geo_scope).

    - `company_lookup_field` : chemin ORM vers la company (défaut : 'company').
    - `zone_lookup_field`    : chemin ORM vers la Zone (ex: 'depot__zone').
    - `depot_lookup_field`   : chemin ORM vers le Dépôt (ex: 'depot').
    - `depot_lookup_fields`  : liste de chemins Dépôt pour les modèles à 2 dépôts
      (filtre OR). Prioritaire sur `depot_lookup_field` si défini.
    Si aucun champ géo n'est pertinent (ex. catalogue produits), laisser à None :
    les rôles voient alors toute leur entreprise.
    """
    company_lookup_field = 'company'
    zone_lookup_field = None
    depot_lookup_field = None
    depot_lookup_fields = None

    def check_permissions(self, request):
        """Bloque le superadmin en défense en profondeur avant tout check de rôle."""
        if request.user and request.user.is_authenticated and request.user.is_superadmin:
            self.permission_denied(
                request,
                message="Le super-administrateur n'a pas accès aux opérations internes des entreprises.",
            )
        super().check_permissions(request)

    def get_queryset(self):
        if hasattr(self, 'queryset'):
            queryset = self.queryset
        elif hasattr(super(), 'get_queryset'):
            queryset = super().get_queryset()
        else:
            raise AttributeError("La vue doit avoir un 'queryset' défini ou implémenter get_queryset()")

        user = self.request.user

        user_company = user.company
        if not user_company:
            return queryset.none()

        queryset = queryset.filter(**{self.company_lookup_field: user_company})

        return apply_geo_scope(
            queryset, user,
            depot_fields=self.depot_lookup_fields or self.depot_lookup_field,
            zone_field=self.zone_lookup_field,
        )


class DepotFilterMixin:
    """
    Mixin pour filtrer automatiquement les QuerySets par dépôt de l'utilisateur.
    """

    def check_permissions(self, request):
        """Bloque le superadmin en défense en profondeur avant tout check de rôle."""
        if request.user and request.user.is_authenticated and request.user.is_superadmin:
            self.permission_denied(
                request,
                message="Le super-administrateur n'a pas accès aux opérations internes des entreprises.",
            )
        super().check_permissions(request)

    def get_queryset(self):
        """Filtre le queryset par dépôt de l'utilisateur."""
        queryset = super().get_queryset()
        user = self.request.user

        # Les utilisateurs sans dépôt n'ont rien à voir
        user_depot = user.depot
        if not user_depot:
            return queryset.none()

        # Filtrer par dépôt si le modèle a ce champ
        if hasattr(queryset.model, 'depot'):
            return queryset.filter(depot=user_depot)

        return queryset


class BaseCompanyPermission(permissions.BasePermission):
    """
    Permission de base pour les vues company.
    Combine vérification de company et de rôle.
    """

    def __init__(self, allowed_roles: list[str] = None, require_company: bool = True):
        super().__init__()
        self.allowed_roles = allowed_roles or []
        self.require_company = require_company

    def has_permission(self, request: Request, view: View) -> bool:
        """Vérifie les permissions de base."""
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Vérifier le rôle si spécifié
        if self.allowed_roles and user.role not in self.allowed_roles:
            return False

        # Vérifier la company si requis
        if self.require_company and not user.company:
            return False

        return True


# Classes de permission spécifiques pour faciliter l'utilisation


class IsSuperAdminBlocked(permissions.BasePermission):
    """
    Bloque le superadmin des endpoints opérationnels des entreprises.
    Le superadmin gère la plateforme (companies, facturation, dashboard agrégé),
    pas les données métier internes (zones, dépôts, utilisateurs opérationnels).
    """
    message = "Le super-administrateur n'a pas accès aux opérations internes des entreprises."

    def has_permission(self, request: Request, view: View) -> bool:
        if request.user and request.user.is_authenticated and request.user.is_superadmin:
            return False
        return True


class IsAdminOrSuperAdmin(BaseCompanyPermission):
    """Permission pour les admins uniquement (superadmin gère la plateforme, pas les données métier)."""

    def __init__(self):
        super().__init__(allowed_roles=[Role.ADMIN])


class IsSupervisorOrAbove(BaseCompanyPermission):
    """Permission pour les superviseurs et les admins (le superadmin est bloqué sur les données métier)."""

    def __init__(self):
        super().__init__(allowed_roles=[Role.SUPERVISEUR, Role.ADMIN])


class IsCompanyMemberOrReadOnly(IsCompanyMember):
    """
    Permission pour les vues en lecture seule pour les membres de company.
    Les utilisateurs authentifiés peuvent lire, mais seul les membres de company peuvent modifier.
    """

    def has_permission(self, request: Request, view: View) -> bool:
        """Autorise la lecture pour tous les utilisateurs authentifiés."""
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return True

    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """Vérifie l'accès en écriture."""
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return super().has_object_permission(request, view, obj)
