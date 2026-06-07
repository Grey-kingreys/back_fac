"""
apps/notifications/tests/test_notifications.py
Tests API : Notifications (liste, lire, tout-lire).
"""

import pytest
from rest_framework import status

from apps.notifications.models import Notification


NOTIFICATIONS_URL = "/api/notifications/"
TOUT_LIRE_URL = "/api/notifications/tout-lire/"


def notification_url(pk):
    return f"/api/notifications/{pk}/"


def notification_lire_url(pk):
    return f"/api/notifications/{pk}/lire/"


def _create_notification(destinataire, company, type_n=None, titre="Test", message="Msg"):
    return Notification.objects.create(
        destinataire=destinataire,
        company=company,
        type_notification=type_n or Notification.TypeNotification.INFO,
        titre=titre,
        message=message,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/notifications/
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestNotificationList:

    def test_utilisateur_voit_ses_notifications(self, client_admin_a, admin_a, company_a):
        notif = _create_notification(admin_a, company_a)
        res = client_admin_a.get(NOTIFICATIONS_URL)
        assert res.status_code == status.HTTP_200_OK
        ids = [n["id"] for n in res.data["results"]]
        assert notif.id in ids

    def test_utilisateur_ne_voit_pas_notifications_autre(
        self, client_admin_a, admin_b, company_b,
    ):
        notif_b = _create_notification(admin_b, company_b)
        res = client_admin_a.get(NOTIFICATIONS_URL)
        ids = [n["id"] for n in res.data["results"]]
        assert notif_b.id not in ids

    def test_filtre_non_lues(self, client_admin_a, admin_a, company_a):
        notif = _create_notification(admin_a, company_a, titre="Non lue")
        notif_lue = _create_notification(admin_a, company_a, titre="Lue")
        notif_lue.est_lue = True
        notif_lue.save(update_fields=["est_lue"])

        res = client_admin_a.get(NOTIFICATIONS_URL, {"non_lues": "true"})
        assert res.status_code == status.HTTP_200_OK
        ids = [n["id"] for n in res.data["results"]]
        assert notif.id in ids
        assert notif_lue.id not in ids

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.get(NOTIFICATIONS_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/notifications/{id}/lire/
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestNotificationLire:

    def test_utilisateur_marque_comme_lue(self, client_admin_a, admin_a, company_a):
        notif = _create_notification(admin_a, company_a)
        assert notif.est_lue is False
        res = client_admin_a.post(notification_lire_url(notif.id))
        assert res.status_code == status.HTTP_200_OK
        notif.refresh_from_db()
        assert notif.est_lue is True

    def test_autre_utilisateur_ne_peut_lire(self, client_admin_b, admin_a, company_a):
        """Admin B ne peut pas marquer la notification de admin A comme lue."""
        notif = _create_notification(admin_a, company_a)
        res = client_admin_b.post(notification_lire_url(notif.id))
        assert res.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_anonyme_refuse(self, anon_client, admin_a, company_a):
        notif = _create_notification(admin_a, company_a)
        res = anon_client.post(notification_lire_url(notif.id))
        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/notifications/tout-lire/
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestNotificationToutLire:

    def test_marque_toutes_lues(self, client_admin_a, admin_a, company_a):
        for i in range(3):
            _create_notification(admin_a, company_a, titre=f"Notif {i}")
        res = client_admin_a.post(TOUT_LIRE_URL)
        assert res.status_code == status.HTTP_200_OK
        non_lues = Notification.objects.filter(destinataire=admin_a, est_lue=False).count()
        assert non_lues == 0

    def test_ne_touche_pas_notifications_autre(
        self, client_admin_a, admin_a, admin_b, company_a, company_b,
    ):
        notif_b = _create_notification(admin_b, company_b)
        client_admin_a.post(TOUT_LIRE_URL)
        notif_b.refresh_from_db()
        assert notif_b.est_lue is False

    def test_anonyme_refuse(self, anon_client):
        res = anon_client.post(TOUT_LIRE_URL)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
