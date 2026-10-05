"""Small shared helpers."""
import json
from datetime import date

from django.utils import timezone


def toast(response, level, text):
    """Attach an HX-Trigger header so app.js shows a toast after an HTMX swap."""
    response["HX-Trigger"] = json.dumps({"toast": {"type": level, "text": text}})
    return response


def next_receipt_no():
    """RCPT-YYYYMMDD-#### sequential per day, race-safe enough for single shop."""
    from sales.models import Sale

    today = timezone.localdate()
    prefix = f"RCPT-{today:%Y%m%d}-"
    last = (
        Sale.objects.filter(receipt_no__startswith=prefix)
        .order_by("-receipt_no")
        .values_list("receipt_no", flat=True)
        .first()
    )
    seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"


def parse_date(value, default=None):
    """Parse YYYY-MM-DD into a date, falling back to `default`."""
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


def date_range_from_request(request, default_days=30):
    """Read ?start=&end= from the request, defaulting to the last N days."""
    end = parse_date(request.GET.get("end"), timezone.localdate())
    start = parse_date(request.GET.get("start"), end - timezone.timedelta(days=default_days - 1))
    if start > end:
        start, end = end, start
    return start, end
