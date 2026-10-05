from django.core.management.base import BaseCommand

from inventory.services import rebuild_stock_cache


class Command(BaseCommand):
    help = "Rebuild Product.current_stock cache from the append-only ledger."

    def handle(self, *args, **options):
        updated = rebuild_stock_cache()
        self.stdout.write(self.style.SUCCESS(f"Stock cache rebuilt; {updated} product(s) corrected."))
