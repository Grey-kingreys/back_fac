# apps/companies/views_company.py
"""
CRUD Company — SuperAdmin uniquement sauf PATCH (Admin pour sa propre company).

Endpoints :
  GET    /api/companies/             — liste toutes les companies (SuperAdmin)
  POST   /api/companies/             — créer company + admin + email (SuperAdmin)
  GET    /api/companies/<id>/        — détail (SuperAdmin ou Admin de cette company)
  PATCH  /api/companies/<id>/        — modifier (SuperAdmin ou Admin de cette company)
  POST   /api/companies/<id>/toggle/ — activer/suspendre (SuperAdmin uniquement)
"""

from django.shortcuts import get_object_or_404

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Company
from .serializers_company import (
    CompanyCreateSerializer,
    CompanyDetailSerializer,
    CompanyListSerializer,
    CompanyUpdateSerializer,
)


def success_response(data=None, message='', status_code=status.HTTP_200_OK):
    return Response(
        {'success': True, 'data': data, 'message': message},
        status=status_code
    )


def error_response(errors=None, message='', status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {'success': False, 'errors': errors, 'message': message},
        status=status_code
    )


class CompanyListCreateView(APIView):
    """
    GET  /api/companies/ — Lister toutes les companies (SuperAdmin)
    POST /api/companies/ — Créer une company + son Admin (SuperAdmin)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Lister toutes les entreprises",
        description=(
            "Retourne la liste de toutes les entreprises de la plateforme.\n\n"
            "**Accès : Super Administrateur uniquement.**\n\n"
            "Filtres : `?is_active=true|false`, `?subscription_plan=free|starter|pro|enterprise`"
        ),
        parameters=[
            OpenApiParameter('is_active', description='true | false'),
            OpenApiParameter('subscription_plan', description='free | starter | pro | enterprise'),
        ],
        responses={
            200: CompanyListSerializer(many=True),
            403: OpenApiResponse(description="Accès réservé au Super Administrateur"),
        },
        tags=["Companies"],
    )
    def get(self, request):
        if request.user.role != 'superadmin':
            return error_response(
                message="Accès réservé au Super Administrateur.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        qs = Company.objects.all().order_by('name')

        is_active = request.query_params.get('is_active')
        plan = request.query_params.get('subscription_plan')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        if plan:
            qs = qs.filter(subscription_plan=plan)

        serializer = CompanyListSerializer(qs, many=True, context={'request': request})
        return success_response(
            data={'count': qs.count(), 'companies': serializer.data},
            message="Liste des entreprises."
        )

    @extend_schema(
        summary="Créer une entreprise",
        description=(
            "Crée une entreprise et son administrateur en un seul appel.\n\n"
            "- La company est créée avec le nom fourni\n"
            "- Un utilisateur Admin est créé avec l'email fourni\n"
            "- Un email est envoyé à l'Admin avec un lien de première connexion "
            "(token usage unique, sans expiration)\n"
            "- L'Admin définit son mot de passe via ce lien et configure ensuite "
            "sa company librement\n\n"
            "**Accès : Super Administrateur uniquement.**"
        ),
        request=CompanyCreateSerializer,
        responses={
            201: CompanyDetailSerializer,
            400: OpenApiResponse(description="Nom déjà pris ou email déjà utilisé"),
            403: OpenApiResponse(description="Accès réservé au Super Administrateur"),
        },
        tags=["Companies"],
    )
    def post(self, request):
        if request.user.role != 'superadmin':
            return error_response(
                message="Accès réservé au Super Administrateur.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = CompanyCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            company = serializer.save()
            return success_response(
                data=serializer.to_representation(company),
                message=(
                    f"Entreprise '{company.name}' créée. "
                    "Un email a été envoyé à l'administrateur."
                ),
                status_code=status.HTTP_201_CREATED
            )
        return error_response(errors=serializer.errors, message="Données invalides.")


class CompanyDetailView(APIView):
    """
    GET   /api/companies/<id>/ — Détail (SuperAdmin ou Admin de cette company)
    PATCH /api/companies/<id>/ — Modifier (SuperAdmin ou Admin de cette company)
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        """
        SuperAdmin : accès à n'importe quelle company.
        Admin : accès uniquement à SA company.
        """
        company = get_object_or_404(Company, pk=pk)

        if request.user.role == 'superadmin':
            return company

        if request.user.role == 'admin' and request.user.company == company:
            return company

        return None

    @extend_schema(
        summary="Détail d'une entreprise",
        description=(
            "**SuperAdmin** : accès à n'importe quelle entreprise.\n\n"
            "**Admin** : accès uniquement à sa propre entreprise."
        ),
        responses={
            200: CompanyDetailSerializer,
            403: OpenApiResponse(description="Accès refusé"),
            404: OpenApiResponse(description="Entreprise introuvable"),
        },
        tags=["Companies"],
    )
    def get(self, request, pk):
        company = self.get_object(pk, request)
        if company is None:
            return error_response(
                message="Accès refusé à cette entreprise.",
                status_code=status.HTTP_403_FORBIDDEN
            )
        serializer = CompanyDetailSerializer(company, context={'request': request})
        return success_response(data=serializer.data)

    @extend_schema(
        summary="Modifier une entreprise",
        description=(
            "**SuperAdmin** : peut modifier n'importe quelle entreprise.\n\n"
            "**Admin** : peut modifier uniquement sa propre entreprise "
            "(nom, logo, plan, settings).\n\n"
            "L'activation/suspension se fait via l'endpoint `/toggle/` "
            "réservé au SuperAdmin."
        ),
        request=CompanyUpdateSerializer,
        responses={
            200: CompanyDetailSerializer,
            400: OpenApiResponse(description="Données invalides"),
            403: OpenApiResponse(description="Accès refusé"),
            404: OpenApiResponse(description="Entreprise introuvable"),
        },
        tags=["Companies"],
    )
    def patch(self, request, pk):
        company = self.get_object(pk, request)
        if company is None:
            return error_response(
                message="Accès refusé à cette entreprise.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = CompanyUpdateSerializer(
            company, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=CompanyDetailSerializer(company, context={'request': request}).data,
                message=f"Entreprise '{company.name}' mise à jour."
            )
        return error_response(errors=serializer.errors, message="Données invalides.")


class CompanyToggleView(APIView):
    """
    POST /api/companies/<id>/toggle/
    Active ou suspend une company — SuperAdmin uniquement.
    Quand suspendue, tous les utilisateurs de cette company
    ne peuvent plus se connecter.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Activer / Suspendre une entreprise",
        description=(
            "Bascule l'état `is_active` de l'entreprise.\n\n"
            "Quand une entreprise est suspendue, tous ses utilisateurs "
            "reçoivent une erreur 403 à la connexion.\n\n"
            "**Accès : Super Administrateur uniquement.**"
        ),
        request=None,
        responses={
            200: CompanyDetailSerializer,
            403: OpenApiResponse(description="Accès réservé au Super Administrateur"),
            404: OpenApiResponse(description="Entreprise introuvable"),
        },
        tags=["Companies"],
    )
    def post(self, request, pk):
        if request.user.role != 'superadmin':
            return error_response(
                message="Accès réservé au Super Administrateur.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        company = get_object_or_404(Company, pk=pk)
        company.is_active = not company.is_active
        company.save(update_fields=['is_active'])

        statut = "activée" if company.is_active else "suspendue"
        return success_response(
            data=CompanyDetailSerializer(company, context={'request': request}).data,
            message=f"Entreprise '{company.name}' {statut}."
        )
