import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import Profile

User = get_user_model()

def test_all_url_views():
    print("=" * 70)
    print("🔍 TESTING URL VIEWS STATUS CODES")
    print("=" * 70)

    client = Client()

    # Get or create test farmer
    farmer, _ = User.objects.get_or_create(username="test_farmer_view_check")
    Profile.objects.get_or_create(user=farmer, defaults={"role": "FARMER", "district": "Lucknow"})
    client.force_login(farmer)

    urls_to_test = [
        "/dashboard/farmer/",
        "/produce/my-produce/",
        "/procurement/centers/",
        "/appointments/",
        "/appointments/book/",
        "/tokens/",
        "/notifications/",
        "/payments/",
    ]

    all_passed = True
    for url in urls_to_test:
        response = client.get(url)
        status = response.status_code
        if status in [200, 302]:
            print(f"  🟢 {url} --> Status {status}")
        else:
            print(f"  🔴 {url} --> Status {status}")
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("🎉 ALL TESTED VIEWS LOADED CLEANLY WITH NO FIELDERRORS!")
    else:
        print("⚠️ SOME VIEWS ENCOUNTERED ERRORS")
    print("=" * 70)

if __name__ == "__main__":
    test_all_url_views()
