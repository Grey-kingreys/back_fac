"""
apps/logistique/views.py
Véhicules, Missions, GPS
"""

from django.utils import timezone

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import CompanyFilterMixin, HasRole

from .models import (
    ConsommationCarburant,
    DocumentVehicule,
    LigneMission,
    Maintenance,
    Mission,
    Panne,
    PositionGPS,
    Vehicule,
)
from .serializers import (
    ConsommationCarburantSerializer,
    DocumentVehiculeSerializer,
    LigneMissionSerializer,
    MaintenanceSerializer,
    MissionCreateSerializer,
    MissionDetailSerializer,
    MissionListSerializer,
    PanneSerializer,
    PositionGPSSerializer,
    SignatureArriveeSerializer,
    VehiculeSerializer,
)


# Lecture logistique : admin, superviseur, gestionnaire (voit missions de son dépôt), chauffeur, maintenancier
LOG_READ = [Role.ADMIN, Role.SUPERVISEUR, Role.GESTIONNAIRE_STOCK, Role.CHAUFFEUR, Role.MAINTENANCIER]
# Écriture véhicules : admin uniquement (configuration de la flotte)
LOG_WRITE_VEHICLE = [Role.ADMIN]
# Initiation mission : admin + gestionnaire (responsable du dépôt)
LOG_WRITE_MISSION = [Role.ADMIN, Role.GESTIONNAIRE_STOCK]
# Validation mission (terminer/annuler) : admin + superviseur
LOG_VALIDATE_MISSION = [Role.ADMIN, Role.SUPERVISEUR]


# ── Véhicules ─────────────────────────────────────────────────────────────────

@extend_schema(tags=["Logistique — Véhicules"])
class VehiculeViewSet(CompanyFilterMixin, GenericViewSet,
                      ListModelMixin, RetrieveModelMixin):

    queryset = Vehicule.objects.order_by('immatriculation')
    serializer_class = VehiculeSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(LOG_READ)]
        return [IsAuthenticated(), HasRole(LOG_WRITE_VEHICLE)]

    def create(self, request, *args, **kwargs):
        s = VehiculeSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = VehiculeSerializer(obj, data=request.data, partial=True,
                               context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.statut == Vehicule.Statut.EN_MISSION:
            raise ValidationError("Impossible de désactiver un véhicule en mission.")
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'detail': f"Véhicule '{obj.immatriculation}' désactivé."})


# ── Missions ──────────────────────────────────────────────────────────────────

@extend_schema(tags=["Logistique — Missions"])
class MissionViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(LOG_READ)]

    def get_serializer_class(self):
        return MissionListSerializer if self.action == 'list' else MissionDetailSerializer

    def get_queryset(self):
        qs = Mission.objects.select_related(
            'vehicule', 'chauffeur', 'depot_depart', 'depot_arrivee',
        ).prefetch_related('lignes__produit', 'positions').order_by('-created_at')

        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(company=company)
        if user.role == Role.CHAUFFEUR:
            qs = qs.filter(chauffeur=user)
        elif user.role == Role.GESTIONNAIRE_STOCK and user.depot:
            # Le gestionnaire voit les missions qui partent ou arrivent à son dépôt
            qs = qs.filter(depot_depart=user.depot)

        statut = self.request.query_params.get('statut')
        vehicule = self.request.query_params.get('vehicule')
        chauffeur = self.request.query_params.get('chauffeur')
        if statut:
            qs = qs.filter(statut=statut)
        if vehicule:
            qs = qs.filter(vehicule_id=vehicule)
        if chauffeur:
            qs = qs.filter(chauffeur_id=chauffeur)
        return qs

    @extend_schema(summary="Créer une mission")
    def create(self, request, *args, **kwargs):
        if not HasRole(LOG_WRITE_MISSION).has_permission(request, self):
            raise PermissionDenied("Seul le gestionnaire ou l'admin peut initier une mission.")
        s = MissionCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        company = request.user.company
        if not company:
            raise ValidationError("Pas d'entreprise associée.")

        from apps.companies.models import Depot
        try:
            vehicule = Vehicule.objects.get(pk=d['vehicule'], company=company, is_active=True)
        except Vehicule.DoesNotExist:
            raise ValidationError({'vehicule': "Véhicule introuvable ou inactif."})

        if vehicule.statut == Vehicule.Statut.EN_MISSION:
            raise ValidationError("Ce véhicule est déjà en mission.")

        from apps.accounts.models import CustomUser
        try:
            chauffeur = CustomUser.objects.get(
                pk=d['chauffeur'], company=company, role=Role.CHAUFFEUR, is_active=True)
        except CustomUser.DoesNotExist:
            raise ValidationError({'chauffeur': "Chauffeur introuvable."})

        try:
            depot_depart = Depot.objects.get(pk=d['depot_depart'], is_active=True)
            depot_arrivee = Depot.objects.get(pk=d['depot_arrivee'], is_active=True)
        except Depot.DoesNotExist:
            raise ValidationError("Dépôt(s) introuvable(s) ou inactif(s).")

        transfert = None
        if d.get('transfert_stock'):
            from apps.stocks.models import TransfertStock
            try:
                transfert = TransfertStock.objects.get(
                    pk=d['transfert_stock'], company=company)
            except TransfertStock.DoesNotExist:
                raise ValidationError({'transfert_stock': "Transfert de stock introuvable."})

        mission = Mission.objects.create(
            company=company, vehicule=vehicule, chauffeur=chauffeur,
            depot_depart=depot_depart, depot_arrivee=depot_arrivee,
            date_depart_prevue=d.get('date_depart_prevue'),
            notes=d.get('notes', ''),
            transfert_stock=transfert,
            created_by=request.user,
        )
        for ligne_data in d.get('lignes', []):
            from apps.produits.models import Produit
            try:
                produit = Produit.objects.get(
                    pk=ligne_data['produit'], company=company, is_active=True)
            except Produit.DoesNotExist:
                raise ValidationError(f"Produit #{ligne_data['produit']} introuvable.")
            LigneMission.objects.create(
                mission=mission, produit=produit, quantite=ligne_data['quantite'])

        vehicule.statut = Vehicule.Statut.EN_MISSION
        vehicule.save(update_fields=['statut'])

        return Response(
            MissionDetailSerializer(mission).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Démarrer le chargement")
    @action(detail=True, methods=['post'], url_path='chargement')
    def chargement(self, request, pk=None):
        if not HasRole(LOG_WRITE_MISSION).has_permission(request, self):
            raise PermissionDenied("Seul le gestionnaire ou l'admin peut démarrer le chargement.")
        mission = self.get_object()
        if mission.statut != Mission.Statut.PLANIFIEE:
            raise ValidationError("La mission doit être à l'état Planifiée.")
        mission.statut = Mission.Statut.CHARGEMENT
        mission.save(update_fields=['statut'])
        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Démarrer le transit")
    @action(detail=True, methods=['post'], url_path='transit')
    def transit(self, request, pk=None):
        mission = self.get_object()
        if mission.statut != Mission.Statut.CHARGEMENT:
            raise ValidationError("La mission doit être à l'état En chargement.")
        mission.statut = Mission.Statut.EN_TRANSIT
        mission.date_depart_reelle = timezone.now()
        mission.save(update_fields=['statut', 'date_depart_reelle'])
        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Signaler l'arrivée avec signature")
    @action(detail=True, methods=['post'], url_path='arrivee')
    def arrivee(self, request, pk=None):
        mission = self.get_object()
        if mission.statut != Mission.Statut.EN_TRANSIT:
            raise ValidationError("La mission doit être en transit.")

        s = SignatureArriveeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        mission.signature_arrivee = d['signature']
        mission.date_arrivee_reelle = timezone.now()

        if d.get('quantites_recues'):
            for item in d['quantites_recues']:
                try:
                    ligne = LigneMission.objects.get(
                        pk=item['ligne_id'], mission=mission)
                    ligne.quantite_recue = item.get('quantite_recue', ligne.quantite)
                    if item.get('observations'):
                        ligne.observations = item['observations']
                    ligne.save()
                except LigneMission.DoesNotExist:
                    pass

        has_litige = any(
            lig.quantite_recue is not None and lig.quantite_recue < lig.quantite
            for lig in mission.lignes.all()
        )
        if has_litige:
            mission.statut = Mission.Statut.LITIGE
            mission.motif_litige = d.get('motif_litige', "Écart de quantité à l'arrivée.")
        else:
            mission.statut = Mission.Statut.ARRIVEE

        mission.save(update_fields=[
            'statut', 'signature_arrivee', 'date_arrivee_reelle', 'motif_litige'])
        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Terminer la mission")
    @action(detail=True, methods=['post'], url_path='terminer')
    def terminer(self, request, pk=None):
        if not HasRole(LOG_VALIDATE_MISSION).has_permission(request, self):
            raise PermissionDenied("Seul le superviseur ou l'admin peut terminer une mission.")
        mission = self.get_object()
        if mission.statut not in (Mission.Statut.ARRIVEE, Mission.Statut.LITIGE):
            raise ValidationError("La mission doit être Arrivée ou en Litige pour être terminée.")
        if mission.statut == Mission.Statut.ARRIVEE and not mission.signature_arrivee:
            raise ValidationError("La signature de réception est obligatoire avant de terminer.")
        mission.statut = Mission.Statut.TERMINEE
        mission.save(update_fields=['statut'])

        mission.vehicule.statut = Vehicule.Statut.DISPONIBLE
        mission.vehicule.save(update_fields=['statut'])

        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Annuler une mission")
    @action(detail=True, methods=['post'], url_path='annuler')
    def annuler(self, request, pk=None):
        if not HasRole(LOG_VALIDATE_MISSION).has_permission(request, self):
            raise PermissionDenied("Seul le superviseur ou l'admin peut annuler une mission.")
        mission = self.get_object()
        if mission.statut in (Mission.Statut.TERMINEE, Mission.Statut.ANNULEE):
            raise ValidationError("Impossible d'annuler cette mission.")
        mission.statut = Mission.Statut.ANNULEE
        mission.save(update_fields=['statut'])

        if mission.vehicule.statut == Vehicule.Statut.EN_MISSION:
            mission.vehicule.statut = Vehicule.Statut.DISPONIBLE
            mission.vehicule.save(update_fields=['statut'])

        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Enregistrer la position GPS du véhicule")
    @action(detail=True, methods=['post'], url_path='position')
    def position(self, request, pk=None):
        mission = self.get_object()
        if mission.statut != Mission.Statut.EN_TRANSIT:
            raise ValidationError("Positions GPS uniquement pour les missions en transit.")
        if request.user != mission.chauffeur:
            raise PermissionDenied("Seul le chauffeur assigné peut envoyer sa position.")

        s = PositionGPSSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        pos = PositionGPS.objects.create(mission=mission, **s.validated_data)
        return Response(PositionGPSSerializer(pos).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Lister les positions GPS d'une mission")
    @action(detail=True, methods=['get'], url_path='positions')
    def positions(self, request, pk=None):
        mission = self.get_object()
        qs = mission.positions.order_by('-enregistre_le')
        return Response(PositionGPSSerializer(qs, many=True).data)

    @extend_schema(summary="Obtenir le QR code d'une mission (image PNG base64)")
    @action(detail=True, methods=['get'], url_path='qr')
    def qr(self, request, pk=None):
        import base64
        from io import BytesIO

        from django.http import HttpResponse

        import qrcode

        mission = self.get_object()
        img = qrcode.make(str(mission.qr_code))
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode('utf-8')
        return Response({'qr_code': str(mission.qr_code), 'image_base64': b64})

    @extend_schema(summary="Scanner le QR code — passe la mission en CHARGEMENT")
    @action(detail=False, methods=['post'], url_path='scanner-qr')
    def scanner_qr(self, request):
        qr_value = request.data.get('qr_code')
        if not qr_value:
            raise ValidationError({'qr_code': "Ce champ est obligatoire."})
        try:
            import uuid
            mission = Mission.objects.get(qr_code=uuid.UUID(str(qr_value)))
        except (Mission.DoesNotExist, ValueError):
            raise ValidationError("QR code invalide ou mission introuvable.")
        if mission.statut != Mission.Statut.PLANIFIEE:
            raise ValidationError(
                f"La mission est en statut '{mission.get_statut_display()}', "
                "seules les missions Planifiées peuvent être scannées.")
        if request.user != mission.chauffeur:
            raise PermissionDenied("Ce QR code ne correspond pas à votre mission.")
        mission.statut = Mission.Statut.CHARGEMENT
        mission.save(update_fields=['statut'])
        return Response(MissionDetailSerializer(mission).data)

    @extend_schema(summary="Bon de livraison PDF signé")
    @action(detail=True, methods=['get'], url_path='bon-livraison')
    def bon_livraison_pdf(self, request, pk=None):
        from io import BytesIO

        from django.http import HttpResponse

        import reportlab.lib.pagesizes as ps
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Table, TableStyle

        mission = self.get_object()
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=ps.A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"BON DE LIVRAISON — {mission.numero}", styles['Title']))
        elements.append(Paragraph(
            f"Date départ : {mission.date_depart_reelle or mission.date_depart_prevue or '—'}",
            styles['Normal']))
        elements.append(Paragraph(
            f"Chauffeur : {mission.chauffeur.get_full_name()}", styles['Normal']))
        elements.append(Paragraph(
            f"Véhicule : {mission.vehicule.immatriculation}", styles['Normal']))
        elements.append(Paragraph(
            f"De : {mission.depot_depart.code} → {mission.depot_arrivee.code}",
            styles['Normal']))

        data = [["Référence", "Produit", "Qté envoyée", "Qté reçue"]]
        for ligne in mission.lignes.select_related('produit'):
            data.append([
                ligne.produit.reference,
                ligne.produit.nom,
                str(ligne.quantite),
                str(ligne.quantite_recue) if ligne.quantite_recue is not None else '—',
            ])
        t = Table(data, colWidths=[80, 200, 90, 90])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(t)

        if mission.signature_arrivee:
            import base64
            elements.append(Paragraph("Signature à l'arrivée :", styles['Normal']))
            sig_data = mission.signature_arrivee
            if sig_data.startswith('data:'):
                sig_data = sig_data.split(',', 1)[-1]
            sig_bytes = base64.b64decode(sig_data)
            sig_buf = BytesIO(sig_bytes)
            elements.append(Image(sig_buf, width=200, height=80))

        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="bl-mission-{mission.numero}.pdf"')
        return response


# ── Maintenance ───────────────────────────────────────────────────────────────

@extend_schema(tags=["Logistique — Maintenance"])
class MaintenanceViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = MaintenanceSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(LOG_READ)]
        return [IsAuthenticated(), HasRole([Role.ADMIN, Role.MAINTENANCIER])]

    def get_queryset(self):
        qs = Maintenance.objects.select_related(
            'vehicule', 'effectue_par'
        ).order_by('-date_planifiee')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(vehicule__company=company)
        vehicule = self.request.query_params.get('vehicule')
        statut = self.request.query_params.get('statut')
        if vehicule:
            qs = qs.filter(vehicule_id=vehicule)
        if statut:
            qs = qs.filter(statut=statut)
        return qs

    def create(self, request, *args, **kwargs):
        s = MaintenanceSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        s = MaintenanceSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


# ── Pannes ────────────────────────────────────────────────────────────────────

@extend_schema(tags=["Logistique — Pannes"])
class PanneViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = PanneSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(LOG_READ)]

    def get_queryset(self):
        qs = Panne.objects.select_related(
            'vehicule', 'declare_par', 'mission'
        ).order_by('-date_declaration')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(vehicule__company=company)
        return qs

    def create(self, request, *args, **kwargs):
        s = PanneSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(declare_par=request.user)
        return Response(s.data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Marquer une panne comme résolue")
    @action(detail=True, methods=['post'], url_path='resoudre')
    def resoudre(self, request, pk=None):
        if not HasRole([Role.ADMIN, Role.SUPERVISEUR, Role.MAINTENANCIER]).has_permission(request, self):
            raise PermissionDenied("Seul le maintenancier, superviseur ou admin peut résoudre une panne.")
        panne = self.get_object()
        if panne.statut == Panne.Statut.RESOLUE:
            raise ValidationError("Cette panne est déjà résolue.")
        cout = request.data.get('cout_reparation')
        panne.statut = Panne.Statut.RESOLUE
        panne.resolu_le = timezone.now()
        if cout is not None:
            panne.cout_reparation = cout
        panne.save(update_fields=['statut', 'resolu_le', 'cout_reparation'])
        if panne.vehicule.statut == Vehicule.Statut.HORS_SERVICE:
            panne.vehicule.statut = Vehicule.Statut.DISPONIBLE
            panne.vehicule.save(update_fields=['statut'])
        return Response(PanneSerializer(panne).data)


# ── Documents véhicule ────────────────────────────────────────────────────────

@extend_schema(tags=["Logistique — Documents"])
class DocumentVehiculeViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):

    serializer_class = DocumentVehiculeSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), HasRole(LOG_READ)]
        return [IsAuthenticated(), HasRole([Role.ADMIN, Role.MAINTENANCIER])]

    def get_queryset(self):
        qs = DocumentVehicule.objects.select_related(
            'vehicule'
        ).order_by('-created_at')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(vehicule__company=company)
        vehicule = self.request.query_params.get('vehicule')
        if vehicule:
            qs = qs.filter(vehicule_id=vehicule)
        return qs

    def create(self, request, *args, **kwargs):
        s = DocumentVehiculeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Consommation carburant ────────────────────────────────────────────────────
@extend_schema(tags=["Logistique — Carburant"])
class ConsommationCarburantViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    serializer_class = ConsommationCarburantSerializer
    LOGI_ROLES = [Role.ADMIN, Role.CHAUFFEUR, Role.MAINTENANCIER]

    def get_permissions(self):
        return [IsAuthenticated(), HasRole(self.LOGI_ROLES)]

    def get_queryset(self):
        qs = ConsommationCarburant.objects.select_related(
            'vehicule', 'mission', 'enregistre_par'
        ).order_by('-date_plein')
        user = self.request.user
        company = user.company
        if not company:
            return qs.none()
        qs = qs.filter(vehicule__company=company)
        vehicule = self.request.query_params.get('vehicule')
        if vehicule:
            qs = qs.filter(vehicule_id=vehicule)
        return qs

    def create(self, request, *args, **kwargs):
        s = ConsommationCarburantSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = s.save(enregistre_par=request.user)
        # Mettre à jour le kilométrage du véhicule si supérieur
        vehicule = obj.vehicule
        if obj.kilometrage > vehicule.kilometrage_actuel:
            vehicule.kilometrage_actuel = obj.kilometrage
            vehicule.save(update_fields=['kilometrage_actuel'])
        return Response(ConsommationCarburantSerializer(obj).data, status=status.HTTP_201_CREATED)
