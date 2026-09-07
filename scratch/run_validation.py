import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from scratch.test_views import test_all_url_views
from scratch.test_flow import test_full_farmer_journey

if __name__ == "__main__":
    test_all_url_views()
    test_full_farmer_journey()
