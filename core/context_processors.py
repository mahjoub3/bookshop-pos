from .models import Setting


def shop_settings(request):
    """Make shop settings available in every template as `shop`."""
    return {"shop": Setting.load()}
