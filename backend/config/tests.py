from django.test import SimpleTestCase
from django.urls import Resolver404, resolve, reverse


class AdminRoutingTests(SimpleTestCase):
    def test_django_admin_has_its_own_prefix(self):
        self.assertEqual(reverse("admin:index"), "/django-admin/")
        self.assertEqual(reverse("admin:login"), "/django-admin/login/")

    def test_django_admin_redirects_to_its_own_login(self):
        response = self.client.get("/django-admin/")
        self.assertRedirects(
            response,
            "/django-admin/login/?next=/django-admin/",
            fetch_redirect_response=False,
        )

    def test_react_admin_routes_are_not_handled_by_django(self):
        for route in ("/admin/", "/admin/users", "/admin/venues",
                      "/admin/suppliers", "/admin/tables"):
            with self.subTest(route=route), self.assertRaises(Resolver404):
                resolve(route)


class EnglishInterfaceTests(SimpleTestCase):
    def test_admin_login_is_in_english(self):
        response = self.client.get(reverse("admin:login"))
        self.assertContains(response, 'lang="en-us"')
        self.assertContains(response, "Bar Inventory administration")
        self.assertContains(response, "Username:")
        self.assertContains(response, "Password:")
        self.assertContains(response, 'value="Log in"')

    def test_role_and_status_labels_are_in_english(self):
        from apps.accounts.models import Role
        from apps.orders.models import OrderStatus
        from apps.tables.models import TableStatus

        self.assertEqual(list(Role.labels), ["Administrator", "Cashier", "Waiter"])
        self.assertEqual(list(OrderStatus.labels), ["Open", "In cashier", "Cancelled", "Paid"])
        self.assertEqual(list(TableStatus.labels), ["Free", "Occupied"])

    def test_framework_validation_uses_english(self):
        from rest_framework import serializers

        with self.assertRaises(serializers.ValidationError) as error:
            serializers.IntegerField().run_validation("invalid")
        self.assertEqual(str(error.exception.detail[0]), "A valid integer is required.")
