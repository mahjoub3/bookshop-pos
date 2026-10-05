"""Service-level tests: sale, stock, credit, profit, aging."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from customers import services as customer_services
from inventory import services as stock_services
from inventory.models import InventoryTransaction
from reports import services as report_services
from reports.models import Expense
from sales import services as sale_services
from sales.models import Return, Sale

from .factories import CustomerFactory, ProductFactory, UserFactory

pytestmark = pytest.mark.django_db


def make_cart(product, qty=1, price=None):
    return {
        "items": {str(product.pk): {
            "qty": qty, "price": str(price or product.sell_price), "discount": "0.00",
        }},
        "customer_id": None, "discount": "0.00",
    }


def stock_product(qty=10):
    product = ProductFactory()
    stock_services.post_transaction(
        product=product, txn_type="adjustment", quantity_delta=qty,
        unit_cost=product.cost_price, note="opening",
    )
    product.refresh_from_db()
    return product


# ---------------------------------------------------------------------------
# Stock service
# ---------------------------------------------------------------------------

class TestStockService:
    def test_ledger_is_source_of_truth(self):
        product = stock_product(10)
        assert stock_services.current_stock(product) == 10
        assert product.current_stock == 10  # cache updated by signal

    def test_negative_and_positive_deltas(self):
        product = stock_product(10)
        stock_services.post_transaction(
            product=product, txn_type="sale", quantity_delta=-3,
        )
        assert stock_services.current_stock(product) == 7

    def test_zero_delta_rejected(self):
        product = stock_product()
        with pytest.raises(ValueError):
            stock_services.post_transaction(
                product=product, txn_type="adjustment", quantity_delta=0,
            )

    def test_stocktake_posts_corrections(self):
        product = stock_product(10)
        txns = stock_services.stocktake(counts={product.pk: 7}, user=None)
        assert len(txns) == 1
        product.refresh_from_db()
        assert product.current_stock == 7

    def test_stocktake_no_change_no_corrections(self):
        product = stock_product(10)
        assert stock_services.stocktake(counts={product.pk: 10}, user=None) == []

    def test_rebuild_stock_cache(self):
        product = stock_product(10)
        # Corrupt the cache, then rebuild
        type(product).objects.filter(pk=product.pk).update(current_stock=999)
        assert stock_services.rebuild_stock_cache() == 1
        product.refresh_from_db()
        assert product.current_stock == 10


# ---------------------------------------------------------------------------
# Sale service
# ---------------------------------------------------------------------------

class TestSaleService:
    def test_create_sale_happy_path(self):
        user = UserFactory()
        product = stock_product(10)
        cart = make_cart(product, qty=2)
        totals = sale_services.cart_totals(cart)
        sale = sale_services.create_sale(
            user=user, cart=cart,
            payments=[{"method": "cash", "amount": totals["total"]}],
        )
        assert sale.payment_status == Sale.PaymentStatus.PAID
        assert sale.amount_due == Decimal("0.00")
        product.refresh_from_db()
        assert product.current_stock == 8
        assert InventoryTransaction.objects.filter(
            reference_type="sale", reference_id=sale.pk
        ).count() == 1

    def test_cost_snapshot_survives_cost_change(self):
        user = UserFactory()
        product = stock_product(10)
        sale = sale_services.create_sale(
            user=user, cart=make_cart(product),
            payments=[{"method": "cash", "amount": sale_services.cart_totals(make_cart(product))["total"]}],
        )
        item = sale.items.get()
        assert item.unit_cost == Decimal("10.00")
        # Later cost update must not change historical profit
        product.cost_price = Decimal("50.00")
        product.save()
        assert sale.items.get().line_profit == Decimal("5.00")  # 15 - 10

    def test_empty_cart_rejected(self):
        with pytest.raises(ValidationError, match="zero items"):
            sale_services.create_sale(
                user=UserFactory(), cart={"items": {}, "discount": "0.00"}, payments=[],
            )

    def test_negative_stock_blocked_without_override(self):
        product = stock_product(1)
        with pytest.raises(ValidationError, match="Not enough stock"):
            sale_services.create_sale(
                user=UserFactory(), cart=make_cart(product, qty=5),
                payments=[{"method": "cash", "amount": "75.00"}],
            )

    def test_negative_stock_allowed_with_override(self):
        product = stock_product(1)
        sale = sale_services.create_sale(
            user=UserFactory(), cart=make_cart(product, qty=5),
            payments=[{"method": "cash", "amount": "75.00"}],
            allow_negative_stock=True,
        )
        assert sale.pk
        product.refresh_from_db()
        assert product.current_stock == -4

    def test_zero_payment_rejected(self):
        product = stock_product()
        with pytest.raises(ValidationError, match="greater than zero"):
            sale_services.create_sale(
                user=UserFactory(), cart=make_cart(product),
                payments=[{"method": "cash", "amount": "0"}],
            )

    def test_credit_sale_requires_customer(self):
        product = stock_product()
        with pytest.raises(ValidationError, match="requires a customer"):
            sale_services.create_sale(
                user=UserFactory(), cart=make_cart(product), payments=[],
            )

    def test_credit_sale_creates_due(self):
        product = stock_product()
        customer = CustomerFactory()
        sale = sale_services.create_sale(
            user=UserFactory(), cart=make_cart(product, qty=2),
            payments=[], customer=customer,
        )
        assert sale.payment_status == Sale.PaymentStatus.CREDIT
        assert sale.amount_due == sale.total

    def test_credit_limit_enforced_and_overridable(self):
        product = stock_product(100)
        customer = CustomerFactory(credit_limit="10.00")
        with pytest.raises(ValidationError, match="Credit limit"):
            sale_services.create_sale(
                user=UserFactory(), cart=make_cart(product, qty=2),
                payments=[], customer=customer,
            )
        sale = sale_services.create_sale(
            user=UserFactory(), cart=make_cart(product, qty=2),
            payments=[], customer=customer, override_credit_limit=True,
        )
        assert sale.pk

    def test_partial_payment_status(self):
        product = stock_product()
        customer = CustomerFactory()
        sale = sale_services.create_sale(
            user=UserFactory(), cart=make_cart(product, qty=2),
            payments=[{"method": "cash", "amount": "10.00"}], customer=customer,
        )
        assert sale.payment_status == Sale.PaymentStatus.PARTIAL
        assert sale.amount_due == sale.total - Decimal("10.00")


# ---------------------------------------------------------------------------
# Credit / receivables
# ---------------------------------------------------------------------------

class TestCreditService:
    def _credit_sale(self, customer, qty=1, price="15.00"):
        product = stock_product(50)
        product.sell_price = Decimal(price)
        product.save()
        return sale_services.create_sale(
            user=UserFactory(), cart=make_cart(product, qty=qty, price=price),
            payments=[], customer=customer,
        )

    def test_balance_increases_with_credit_sale(self):
        customer = CustomerFactory()
        self._credit_sale(customer, qty=2)
        assert customer_services.get_balance(customer) == Decimal("30.00")

    def test_payment_decreases_balance(self):
        customer = CustomerFactory()
        sale = self._credit_sale(customer, qty=2)
        customer_services.record_payment(
            customer=customer, amount=Decimal("20.00"), method="cash",
            user=None, sale=sale,
        )
        assert customer_services.get_balance(customer) == Decimal("10.00")
        sale.refresh_from_db()
        assert sale.payment_status == Sale.PaymentStatus.PARTIAL

    def test_full_settlement_marks_paid(self):
        customer = CustomerFactory()
        sale = self._credit_sale(customer)
        customer_services.record_payment(
            customer=customer, amount=sale.total, method="cash", user=None, sale=sale,
        )
        assert customer_services.get_balance(customer) == Decimal("0.00")
        sale.refresh_from_db()
        assert sale.payment_status == Sale.PaymentStatus.PAID

    def test_credit_return_decreases_balance(self):
        customer = CustomerFactory()
        sale = self._credit_sale(customer, qty=2)
        item = sale.items.get()
        sale_services.process_return(
            sale=sale, product=item.product, quantity=1,
            refund_method=Return.RefundMethod.CREDIT, reason="damaged", user=None,
        )
        assert customer_services.get_balance(customer) == Decimal("15.00")

    def test_nonpositive_payment_rejected(self):
        customer = CustomerFactory()
        with pytest.raises(ValidationError):
            customer_services.record_payment(
                customer=customer, amount=Decimal("0"), method="cash", user=None,
            )

    def test_aging_buckets(self):
        customer = CustomerFactory()
        old_sale = self._credit_sale(customer)
        # Backdate the sale 45 days -> lands in the 31-60 bucket
        old_sale.sale_date = timezone.now() - timedelta(days=45)
        old_sale.save(update_fields=["sale_date"])
        new_sale = self._credit_sale(customer)  # current bucket
        report = customer_services.aging_report(customer)
        assert len(report) == 1
        row = report[0]
        assert row["days30"] == old_sale.total
        assert row["current"] == new_sale.total
        assert row["total"] == old_sale.total + new_sale.total

    def test_aging_payment_covers_oldest_first(self):
        customer = CustomerFactory()
        old_sale = self._credit_sale(customer)
        old_sale.sale_date = timezone.now() - timedelta(days=100)
        old_sale.save(update_fields=["sale_date"])
        new_sale = self._credit_sale(customer)
        # Pay exactly the old sale's total -> only the current bucket remains
        customer_services.record_payment(
            customer=customer, amount=old_sale.total, method="cash", user=None,
        )
        row = customer_services.aging_report(customer)[0]
        assert row["days90"] == Decimal("0.00")
        assert row["current"] == new_sale.total


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------

class TestReturns:
    def test_return_reverses_profit_and_restock(self):
        product = stock_product(10)
        customer = CustomerFactory()
        sale = sale_services.create_sale(
            user=UserFactory(), cart=make_cart(product, qty=2),
            payments=[{"method": "cash", "amount": "30.00"}], customer=customer,
        )
        ret = sale_services.process_return(
            sale=sale, product=product, quantity=1,
            refund_method=Return.RefundMethod.CASH, reason="changed mind", user=None,
        )
        product.refresh_from_db()
        assert product.current_stock == 9  # 10 - 2 + 1
        assert ret.profit_reversal == Decimal("5.00")  # 15 - 10

    def test_cannot_return_more_than_sold(self):
        product = stock_product(10)
        sale = sale_services.create_sale(
            user=UserFactory(), cart=make_cart(product, qty=1),
            payments=[{"method": "cash", "amount": "15.00"}],
        )
        with pytest.raises(ValidationError, match="left to return"):
            sale_services.process_return(
                sale=sale, product=product, quantity=2,
                refund_method=Return.RefundMethod.CASH, reason="", user=None,
            )


# ---------------------------------------------------------------------------
# Profit report
# ---------------------------------------------------------------------------

class TestProfitReport:
    def test_gross_and_net_profit(self):
        today = timezone.localdate()
        product = stock_product(50)  # cost 10, price 15
        sale = sale_services.create_sale(
            user=UserFactory(), cart=make_cart(product, qty=4),
            payments=[{"method": "cash", "amount": "60.00"}],
        )
        Expense.objects.create(
            category="rent", description="Shop rent", amount=Decimal("7.50"),
            expense_date=today,
        )
        report = report_services.profit_report(today, today, group_by="day")
        # line profit = (15 - 10) * 4 - 0 = 20; tax rate is 0 in tests
        assert report["gross_profit"] == Decimal("20.00")
        assert report["net_profit"] == Decimal("12.50")  # 20 - 7.50
        assert report["rows"][0]["key"] == today.isoformat()

    def test_profit_grouped_by_product(self):
        today = timezone.localdate()
        p1, p2 = stock_product(50), stock_product(50)
        for p in (p1, p2):
            sale_services.create_sale(
                user=UserFactory(), cart=make_cart(p, qty=1),
                payments=[{"method": "cash", "amount": "15.00"}],
            )
        report = report_services.profit_report(today, today, group_by="product")
        keys = {r["key"] for r in report["rows"]}
        assert keys == {p1.title, p2.title}
