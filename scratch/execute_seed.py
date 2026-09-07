import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kisanflow.settings")
django.setup()

from django.core.management import call_command

def main():
    print("Executing seed_procurement_centers management command...")
    call_command("seed_procurement_centers")

if __name__ == "__main__":
    main()
