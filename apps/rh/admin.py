from django.contrib import admin

from .models import Conge, Document, Employe, HistoriqueAffectation, ObjectifVente, Presence


@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):
    list_display = ['matricule', 'nom_complet', 'company', 'depot',
                    'poste', 'statut', 'date_embauche']
    list_filter = ['company', 'statut', 'depot']
    search_fields = ['matricule', 'nom', 'prenom']


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ['employe', 'date', 'type_presence', 'heure_arrivee', 'heure_depart']
    list_filter = ['employe__company', 'type_presence']
    date_hierarchy = 'date'


@admin.register(Conge)
class CongeAdmin(admin.ModelAdmin):
    list_display = ['employe', 'type_conge', 'date_debut', 'date_fin',
                    'nb_jours', 'statut', 'approuve_par']
    list_filter = ['employe__company', 'type_conge', 'statut']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['titre', 'type_document', 'company', 'employe',
                    'uploade_par', 'created_at']
    list_filter = ['company', 'type_document']
    search_fields = ['titre', 'reference_externe']


@admin.register(ObjectifVente)
class ObjectifVenteAdmin(admin.ModelAdmin):
    list_display = ['depot', 'annee', 'mois', 'montant_objectif',
                    'montant_realise', 'taux_realisation']
    list_filter = ['depot__zone__company', 'annee', 'mois']


@admin.register(HistoriqueAffectation)
class HistoriqueAffectationAdmin(admin.ModelAdmin):
    list_display = ['employe', 'depot_ancien', 'depot_nouveau', 'effectue_par', 'created_at']
    list_filter = ['depot_nouveau__zone__company']
    readonly_fields = ['created_at']
