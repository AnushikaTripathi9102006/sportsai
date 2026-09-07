import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kisanflow.settings")
django.setup()

from django.core.management import call_command
from scratch.test_flow import test_full_farmer_journey

def main():
    print("=" * 80)
    print("1. RUNNING SYNTHETIC PROCUREMENT CENTER SEED COMMAND")
    print("=" * 80)
    call_command("seed_procurement_centers")
    
    print("\n" + "=" * 80)
    print("2. TESTING FARMER JOURNEY & RECOMMENDATION ENGINE WITH SEEDED DATA")
    print("=" * 80)
    test_full_farmer_journey()

if __name__ == "__main__":
    main()
