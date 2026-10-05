# Bookshop — Book & Stationery Shop Management

A complete single-shop management system: stock/inventory (append-only ledger),
POS sales, purchasing, customer credit (accounts receivable) and profit tracking.

**Stack:** Django 5 · HTMX · Alpine.js · Tailwind CSS (CDN) · Chart.js ·
ReportLab (PDF) · openpyxl (Excel) · python-barcode · SQLite (dev) / PostgreSQL (prod).

---

## 1. Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

python manage.py migrate
python manage.py createsuperuser        # creates an admin (superuser => admin role)
python manage.py seed_demo              # optional demo data
python manage.py runserver
```

Open <http://127.0.0.1:8000/> and sign in. The seed command creates `admin/admin`
if no superuser exists — **change that password immediately**.

## 2. Tests

```bash
pytest                # service tests: sale, stock, credit, profit, aging
```

## 3. Roles

| Role    | Capabilities |
|---------|--------------|
| cashier | POS, view products/stock, view own sales |
| manager | Everything except user management and settings |
| admin   | Everything (superusers are always admin) |

Enforced with Django groups (`Admin`/`Manager`/`Cashier`, created on migrate)
plus `role_required` decorators / `RoleRequiredMixin`. Profiles sync group
membership automatically.

**Adding a new role:** add a choice to `accounts.models.Profile.Role`, add the
group name to `Profile.GROUPS`, then use `role_required("admin", "your_role")`
on the views it should reach.

## 4. Business rules (read before modifying)

- **Stock is a ledger.** Current stock = `SUM(InventoryTransaction.quantity_delta)`.
  `Product.current_stock` is only a cache (updated by a signal); rebuild with
  `python manage.py rebuild_stock_cache` or the button in Settings.
- **Cost snapshot.** `SaleItem.unit_cost` copies `Product.cost_price` at sale
  time; historical profit never changes when costs change.
- **Profit.** line = (price − cost) × qty − line discount; gross = Σ lines −
  return reversals; net = gross − expenses. Reports by day/product/category/supplier.
- **Credit.** balance = Σ sales − Σ payments − Σ credit-refunded returns.
  Aging (current / 31–60 / 61–90 / 90+) uses FIFO allocation of payments.
- **Purchasing.** Receiving a PO posts `purchase` ledger entries and updates
  `cost_price` using **last cost**.
- **Soft delete.** Products/customers/sales are never hard-deleted; FKs to
  sales use `on_delete=PROTECT`.
- **Money** is always `DecimalField(12, 2)` — never float.
- Sales, receiving, returns, stocktake all run inside `transaction.atomic()`.

## 5. Data import/export

- **Products:** Catalog → Import CSV (upload → preview → confirm).
  Headers: `title, type, isbn, sku, barcode, author, publisher, category,
  cost_price, sell_price, reorder_level, opening_stock`.
- **Reports:** every report page has Excel (`.xlsx`) and PDF export buttons.
- **Customers:** printable PDF statement per customer.

## 6. Production deployment

### Gunicorn + nginx (bare metal / VPS)

```bash
# .env
DEBUG=False
SECRET_KEY=<long-random-string>
ALLOWED_HOSTS=shop.example.com
DB_ENGINE=postgres  # and POSTGRES_* vars

pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic
gunicorn shop.wsgi:application --bind 127.0.0.1:8000 --workers 2
```

nginx reverse proxy (static files are served by WhiteNoise, so nginx only
needs to proxy):

```nginx
server {
    listen 80;
    server_name shop.example.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Docker

```bash
docker compose up --build
```

The compose stack runs gunicorn + PostgreSQL and migrates on start.

## 7. Backup & restore

- **SQLite:** stop the app (or use the online backup API):
  `sqlite3 db.sqlite3 ".backup backup-$(date +%F).sqlite3"`
  Restore: copy the file back.
- **PostgreSQL:** `pg_dump bookshop > backup-$(date +%F).sql`,
  restore with `psql bookshop < backup-….sql`.

Run nightly via cron and keep copies off the machine.

## 8. Project layout

```text
shop/            project settings, urls, wsgi/asgi
accounts/        users, roles (Profile), auth views, role_required
catalog/         Category, Supplier, Product, CSV import/export, barcode labels
inventory/       append-only stock ledger, adjustments, stocktake, cache rebuild
sales/           POS (HTMX), Sale/SaleItem/Payment/Return, sale + return services
purchasing/      purchase orders, receiving, supplier returns
customers/       customers, credit balance, aging, PDF statements
reports/         daily sales/cash drawer, profit, best sellers, dead stock,
                 receivables aging, expenses, Excel/PDF exports
dashboard/       home KPIs + 30-day sales chart
core/            Setting singleton, template tags, utils, seed command
templates/       base layout + per-app templates (+ HTMX partials)
static/          css/js (Tailwind components, dark mode, toast bridge)
tests/           pytest-django service tests
```
