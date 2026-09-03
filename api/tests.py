from datetime import date

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Profile
from produce.models import Produce


class AuthenticationApiTests(APITestCase):
    register_url = "/api/v1/auth/register/"
    login_url = "/api/v1/auth/login/"
    me_url = "/api/v1/auth/me/"

    def test_farmer_registration_is_approved(self):
        response = self.client.post(self.register_url, {
            "username": "farmer1",
            "email": "farmer@example.com",
            "role": "FARMER",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = Profile.objects.get(user__username="farmer1")
        self.assertEqual(profile.role, "FARMER")
        self.assertTrue(profile.is_approved)
        self.assertEqual(profile.farmer_id, "FAR-0001")

    def test_officer_registration_is_pending(self):
        response = self.client.post(self.register_url, {
            "username": "officer1",
            "email": "officer@example.com",
            "role": "OFFICER",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = Profile.objects.get(user__username="officer1")
        self.assertEqual(profile.role, "OFFICER")
        self.assertFalse(profile.is_approved)

    def test_approved_farmer_can_login_and_get_current_profile(self):
        user = User.objects.create_user(
            username="farmer1",
            password="StrongPassword123!",
        )
        Profile.objects.filter(user=user).update(
            role="FARMER",
            is_approved=True,
        )

        response = self.client.post(self.login_url, {
            "username": "farmer1",
            "password": "StrongPassword123!",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        me_response = self.client.get(self.me_url)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["username"], "farmer1")

    def test_pending_officer_cannot_login(self):
        user = User.objects.create_user(
            username="officer1",
            password="StrongPassword123!",
        )
        Profile.objects.filter(user=user).update(
            role="OFFICER",
            is_approved=False,
        )

        response = self.client.post(self.login_url, {
            "username": "officer1",
            "password": "StrongPassword123!",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("approval", response.data)


class ProduceApiTests(APITestCase):
    list_url = "/api/v1/produce/"

    def setUp(self):
        self.farmer = User.objects.create_user(
            username="farmer1",
            password="StrongPassword123!",
        )
        Profile.objects.filter(user=self.farmer).update(
            role="FARMER",
            is_approved=True,
        )
        self.other_farmer = User.objects.create_user(
            username="farmer2",
            password="StrongPassword123!",
        )
        Profile.objects.filter(user=self.other_farmer).update(
            role="FARMER",
            is_approved=True,
        )
        self.client.force_authenticate(user=self.farmer)

    def test_unauthenticated_user_cannot_list_produce(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_farmer_can_create_and_list_only_own_produce(self):
        own_produce = Produce.objects.create(
            farmer=self.farmer,
            crop_name="Wheat",
            quantity="25.00",
            unit="KG",
            harvest_date=date(2026, 8, 30),
        )
        Produce.objects.create(
            farmer=self.other_farmer,
            crop_name="Rice",
            quantity="10.00",
            unit="KG",
            harvest_date=date(2026, 8, 30),
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], own_produce.id)

        create_response = self.client.post(self.list_url, {
            "crop_name": "Maize",
            "quantity": "12.50",
            "unit": "KG",
            "harvest_date": "2026-08-31",
            "status": "PROCURED",
        }, format="json")
        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
        )
        created = Produce.objects.get(id=create_response.data["id"])
        self.assertEqual(created.farmer, self.farmer)
        self.assertEqual(created.status, "AVAILABLE")

    def test_farmer_cannot_access_another_farmers_produce(self):
        other_produce = Produce.objects.create(
            farmer=self.other_farmer,
            crop_name="Rice",
            quantity="10.00",
            unit="KG",
            harvest_date=date(2026, 8, 30),
        )

        response = self.client.get(f"{self.list_url}{other_produce.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_available_produce_cannot_be_updated_or_deleted(self):
        produce = Produce.objects.create(
            farmer=self.farmer,
            crop_name="Wheat",
            quantity="25.00",
            unit="KG",
            harvest_date=date(2026, 8, 30),
            status="REQUESTED",
        )

        update_response = self.client.patch(
            f"{self.list_url}{produce.id}/",
            {"quantity": "30.00"},
            format="json",
        )
        delete_response = self.client.delete(
            f"{self.list_url}{produce.id}/"
        )

        self.assertEqual(
            update_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertTrue(Produce.objects.filter(id=produce.id).exists())
