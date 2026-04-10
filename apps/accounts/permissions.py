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
        """
        if request.user.is_superadmin:
            return True
            
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
    
    Utilisation :
    permission_classes = [HasRole(['admin', 'superviseur'])]
    """
    
    def __init__(self, allowed_roles: list[str] = None):
        super().__init__()
        self.allowed_roles = allowed_roles or []
    
    def has_permission(self, request: Request, view: View) -> bool:
        """Vérifie le rôle de l'utilisateur."""
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Le superadmin a tous les droits
        if request.user.is_superadmin:
            return True
            
        if not self.allowed_roles:
            return True
            
        return request.user.role in self.allowed_roles


class IsOwnerOrCompanyAdmin(permissions.BasePermission):
    """
    Permission pour les ressources personnelles :
    - L'utilisateur peut accéder à ses propres ressources
    - Les admins/superadmins peuvent accéder aux ressources de leur company
    """
    
    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """Vérifie l'accès à un objet spécifique."""
        user = request.user
        
        # Superadmin a tous les droits
        if user.is_superadmin:
            return True
            
        # L'utilisateur peut accéder à ses propres ressources
        if hasattr(obj, 'user') and obj.user == user:
            return True
            
        if hasattr(obj, 'id') and hasattr(user, 'id') and obj.id == user.id:
            return True
            
        # Les admins peuvent accéder aux ressources de leur company
        if user.is_admin_or_above and hasattr(obj, 'company'):
            return obj.company == user.company
            
        return False


class CompanyFilterMixin:
    """
    Mixin pour filtrer automatiquement les QuerySets par company de l'utilisateur connecté.
    
    Utilisation :
    class MyViewSet(CompanyFilterMixin, viewsets.ModelViewSet):
        queryset = MyModel.objects.all()
        ...
    """
    
    def get_queryset(self):
        """
        Filtre le queryset par company de l'utilisateur.
        Le superadmin voit toutes les données.
        """
        # Utiliser le queryset défini dans la vue ou get_queryset de la classe parente
        if hasattr(self, 'queryset'):
            queryset = self.queryset
        elif hasattr(super(), 'get_queryset'):
            queryset = super().get_queryset()
        else:
            raise AttributeError("La vue doit avoir un 'queryset' défini ou implémenter get_queryset()")
            
        user = self.request.user
        
        # Le superadmin voit tout
        if user.is_superadmin:
            return queryset
            
        # Les autres utilisateurs voient seulement leur company
        user_company = user.company
        if not user_company:
            return queryset.none()
            
        # Filtrer par company si le modèle a ce champ
        if hasattr(queryset.model, 'company'):
            return queryset.filter(company=user_company)
            
        # Filtrer par user si le modèle est lié à un utilisateur
        if hasattr(queryset.model, 'user'):
            return queryset.filter(user__company=user_company)
            
        # Si le modèle n'a ni company ni user, retourner tout (attention !)
        return queryset


class DepotFilterMixin:
    """
    Mixin pour filtrer automatiquement les QuerySets par dépôt de l'utilisateur.
    """
    
    def get_queryset(self):
        """Filtre le queryset par dépôt de l'utilisateur."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Le superadmin voit tout
        if user.is_superadmin:
            return queryset
            
        # Les autres utilisateurs voient seulement leur dépôt
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
            
        # Superadmin a tous les droits
        if user.is_superadmin:
            return True
            
        # Vérifier le rôle si spécifié
        if self.allowed_roles and user.role not in self.allowed_roles:
            return False
            
        # Vérifier la company si requis
        if self.require_company and not user.company:
            return False
            
        return True


# Classes de permission spécifiques pour faciliter l'utilisation
class IsAdminOrSuperAdmin(BaseCompanyPermission):
    """Permission pour les admins et superadmins."""
    def __init__(self):
        super().__init__(allowed_roles=[Role.ADMIN, Role.SUPERADMIN])


class IsSupervisorOrAbove(BaseCompanyPermission):
    """Permission pour les superviseurs et au-dessus."""
    def __init__(self):
        super().__init__(allowed_roles=[Role.SUPERVISEUR, Role.ADMIN, Role.SUPERADMIN])


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
