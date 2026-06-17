"""
apps/rh/serializers.py
"""

from rest_framework import serializers

from .models import Conge, Document, Employe, HistoriqueAffectation, ObjectifVente, Presence


class EmployeListSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    depot_nom = serializers.CharField(source='depot.name', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Employe
        fields = ['id', 'matricule', 'nom', 'prenom', 'nom_complet',
                  'poste', 'depot', 'depot_nom', 'statut', 'statut_label',
                  'telephone', 'created_at']
        read_only_fields = ['id', 'nom_complet', 'depot_nom', 'statut_label', 'created_at']


class EmployeDetailSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    depot_nom = serializers.CharField(source='depot.name', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Employe
        fields = ['id', 'matricule', 'nom', 'prenom', 'nom_complet',
                  'user', 'depot', 'depot_nom', 'poste',
                  'telephone', 'email', 'date_embauche', 'salaire_base',
                  'statut', 'statut_label', 'created_at']
        read_only_fields = ['id', 'nom_complet', 'depot_nom', 'statut_label', 'created_at']

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        return super().create(validated_data)


class PresenceSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_presence_display', read_only=True)
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)

    class Meta:
        model = Presence
        fields = ['id', 'employe', 'employe_nom', 'date', 'type_presence', 'type_label',
                  'heure_arrivee', 'heure_depart', 'observations', 'enregistre_par']
        read_only_fields = ['id', 'type_label', 'employe_nom', 'enregistre_par']

    def create(self, validated_data):
        validated_data['enregistre_par'] = self.context['request'].user
        return super().create(validated_data)


class CongeSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_conge_display', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)
    nb_jours = serializers.IntegerField(read_only=True)

    class Meta:
        model = Conge
        fields = ['id', 'employe', 'employe_nom', 'type_conge', 'type_label',
                  'date_debut', 'date_fin', 'nb_jours', 'statut', 'statut_label',
                  'motif', 'approuve_par', 'created_at']
        read_only_fields = ['id', 'type_label', 'statut_label', 'employe_nom',
                            'nb_jours', 'approuve_par', 'created_at']

    def validate(self, data):
        if data.get('date_fin') and data.get('date_debut'):
            if data['date_fin'] < data['date_debut']:
                raise serializers.ValidationError(
                    "La date de fin doit être après la date de début.")
        return data


class DocumentSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_document_display', read_only=True)
    employe_nom = serializers.SerializerMethodField()
    uploade_par_nom = serializers.CharField(
        source='uploade_par.get_full_name', read_only=True)

    class Meta:
        model = Document
        fields = ['id', 'type_document', 'type_label', 'titre', 'fichier',
                  'employe', 'employe_nom',
                  'commande', 'mission', 'transfert',
                  'reference_externe', 'notes',
                  'uploade_par', 'uploade_par_nom', 'created_at']
        read_only_fields = ['id', 'type_label', 'employe_nom',
                            'uploade_par', 'uploade_par_nom', 'created_at']

    def get_employe_nom(self, obj):
        return obj.employe.nom_complet if obj.employe else None

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        validated_data['uploade_par'] = self.context['request'].user
        return super().create(validated_data)


class ObjectifVenteSerializer(serializers.ModelSerializer):
    depot_nom = serializers.CharField(source='depot.name', read_only=True)
    taux_realisation = serializers.FloatField(read_only=True)

    class Meta:
        model = ObjectifVente
        fields = ['id', 'depot', 'depot_nom', 'annee', 'mois',
                  'montant_objectif', 'montant_realise', 'taux_realisation',
                  'notes', 'created_by']
        read_only_fields = ['id', 'depot_nom', 'taux_realisation', 'created_by']

    def create(self, validated_data):
        validated_data['company'] = self.context['request'].user.company
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class HistoriqueAffectationSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom_complet', read_only=True)
    depot_ancien_code = serializers.SerializerMethodField()
    depot_nouveau_code = serializers.SerializerMethodField()
    effectue_par_nom = serializers.CharField(
        source='effectue_par.get_full_name', read_only=True)

    class Meta:
        model = HistoriqueAffectation
        fields = ['id', 'employe', 'employe_nom',
                  'depot_ancien', 'depot_ancien_code',
                  'depot_nouveau', 'depot_nouveau_code',
                  'motif', 'effectue_par', 'effectue_par_nom', 'created_at']
        read_only_fields = fields

    def get_depot_ancien_code(self, obj):
        return obj.depot_ancien.code if obj.depot_ancien else None

    def get_depot_nouveau_code(self, obj):
        return obj.depot_nouveau.code if obj.depot_nouveau else None
