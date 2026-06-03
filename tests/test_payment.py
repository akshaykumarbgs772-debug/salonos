"""Tests for the SalonOS Payment System"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models import (
    Client, Commission, GiftCard, TipDistribution,
    Transaction, TransactionItem, TransactionStatus,
    TransactionType, User,
)
from app.payment_service import PaymentError, PaymentProcessor


@pytest.fixture
def db_session():
    return MagicMock()


@pytest.fixture
def processor(db_session):
    return PaymentProcessor(db_session)


@pytest.fixture
def sample_items():
    return [
        {"item_type": "service", "item_name": "Balayage", "unit_price": "220.00", "quantity": 1, "stylist_id": str(uuid4())},
        {"item_type": "product", "item_name": "Shampoo", "unit_price": "28.00", "quantity": 2, "stylist_id": str(uuid4())},
    ]


class TestCalculateTotals:
    def test_basic_totals(self, processor, sample_items):
        result = processor.calculate_totals(sample_items)
        assert result["subtotal"] == Decimal("276.00")
        assert result["tax_amount"] == Decimal("0.00")
        assert result["tip_amount"] == Decimal("0.00")
        assert result["total"] == Decimal("276.00")

    def test_with_tip_and_discount(self, processor, sample_items):
        result = processor.calculate_totals(sample_items, tip_amount="30.00", discount_amount="20.00")
        assert result["subtotal"] == Decimal("276.00")
        assert result["tip_amount"] == Decimal("30.00")
        assert result["discount_amount"] == Decimal("20.00")
        assert result["total"] == Decimal("286.00")

    def test_with_tax(self, processor, sample_items):
        result = processor.calculate_totals(sample_items, tax_rate="8.50")
        assert result["tax_amount"] == Decimal("23.46")
        assert result["total"] == Decimal("299.46")

    def test_total_never_negative(self, processor, sample_items):
        result = processor.calculate_totals(sample_items, discount_amount="9999.00")
        assert result["total"] == Decimal("0.00")


class TestProcessPayment:
    def test_client_not_found(self, processor, db_session, sample_items):
        db_session.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(PaymentError, match="Client not found"):
            processor.process_payment(
                client_id=uuid4(),
                processed_by=uuid4(),
                transaction_type="service",
                items=sample_items,
            )

    def test_successful_cash_payment(self, processor, db_session, sample_items):
        client = MagicMock(spec=Client)
        client.id = uuid4()
        client.total_visits = 0
        client.total_spent = Decimal("0.00")

        db_session.query.return_value.filter.return_value.first.return_value = client

        txn = processor.process_payment(
            client_id=client.id,
            processed_by=uuid4(),
            transaction_type="service",
            items=sample_items,
            payment_method="cash",
        )

        assert txn.status == TransactionStatus.completed
        assert txn.subtotal == Decimal("276.00")
        assert txn.total == Decimal("276.00")
        assert client.total_visits == 1
        assert client.total_spent == Decimal("276.00")
        db_session.commit.assert_called()

    def test_tip_distribution(self, processor, db_session, sample_items):
        client = MagicMock(spec=Client)
        client.id = uuid4()
        client.total_visits = 0
        client.total_spent = Decimal("0.00")
        db_session.query.return_value.filter.return_value.first.return_value = client

        stylist_id = uuid4()
        txn = processor.process_payment(
            client_id=client.id,
            processed_by=uuid4(),
            transaction_type="service",
            items=sample_items,
            tip_amount="50.00",
            tip_split=[{"stylist_id": str(stylist_id), "percentage": 100}],
        )

        assert txn.tip_amount == Decimal("50.00")
        tip_calls = [c for c in db_session.add.call_args_list if isinstance(c[0][0], TipDistribution)]
        assert len(tip_calls) == 1
        assert tip_calls[0][0][0].amount == Decimal("50.00")


class TestRefund:
    def test_full_refund(self, processor, db_session):
        original = MagicMock(spec=Transaction)
        original.id = uuid4()
        original.total = Decimal("200.00")
        original.status = TransactionStatus.completed
        original.subtotal = Decimal("200.00")
        original.tax_amount = Decimal("0.00")
        original.tip_amount = Decimal("0.00")
        original.appointment_id = None
        original.client_id = uuid4()
        original.payment_method = "card"

        db_session.query.return_value.filter.return_value.first.return_value = original

        refund = processor.process_refund(
            transaction_id=original.id,
            processed_by=uuid4(),
            reason="Customer dissatisfaction",
        )

        assert refund.transaction_type == TransactionType.refund
        assert refund.total == Decimal("-200.00")
        assert original.status == TransactionStatus.refunded

    def test_partial_refund(self, processor, db_session):
        original = MagicMock(spec=Transaction)
        original.id = uuid4()
        original.total = Decimal("200.00")
        original.status = TransactionStatus.completed
        original.subtotal = Decimal("200.00")
        original.tax_amount = Decimal("0.00")
        original.tip_amount = Decimal("0.00")
        original.appointment_id = None
        original.client_id = uuid4()
        original.payment_method = "card"

        db_session.query.return_value.filter.return_value.first.return_value = original

        refund = processor.process_refund(
            transaction_id=original.id,
            processed_by=uuid4(),
            amount=Decimal("50.00"),
            reason="Partial refund for product return",
        )

        assert refund.total == Decimal("-50.00")
        assert original.status == TransactionStatus.partial_refund


class TestGiftCard:
    def test_issue_gift_card(self, processor, db_session):
        card = processor.issue_gift_card(initial_balance=Decimal("100.00"))
        assert card.original_balance == Decimal("100.00")
        assert card.current_balance == Decimal("100.00")
        assert card.code.startswith("SALON-")
        assert card.is_active is True
        db_session.add.assert_called()
        db_session.commit.assert_called()

    def test_redeem_gift_card(self, processor, db_session):
        card = MagicMock(spec=GiftCard)
        card.id = uuid4()
        card.code = "SALON-TEST1234"
        card.current_balance = Decimal("100.00")
        card.is_active = True
        card.expires_at = None

        db_session.query.return_value.filter.return_value.first.return_value = card

        result = processor.redeem_gift_card(code="SALON-TEST1234", amount=Decimal("30.00"))
        assert result.current_balance == Decimal("70.00")
        assert result.is_active is True

    def test_redeem_exhausted_gift_card(self, processor, db_session):
        card = MagicMock(spec=GiftCard)
        card.code = "SALON-TEST1234"
        card.current_balance = Decimal("100.00")
        card.is_active = True
        card.expires_at = None

        db_session.query.return_value.filter.return_value.first.return_value = card

        result = processor.redeem_gift_card(code="SALON-TEST1234", amount=Decimal("100.00"))
        assert result.current_balance == Decimal("0.00")
        assert result.is_active is False


class TestCommission:
    def test_calculate_commission(self, processor, db_session):
        stylist_id = uuid4()
        transaction_id = uuid4()

        stylist = MagicMock(spec=User)
        stylist.id = stylist_id
        stylist.commission_rate = Decimal("45.00")

        transaction = MagicMock(spec=Transaction)
        transaction.id = transaction_id
        transaction.appointment_id = uuid4()
        transaction.tip_amount = Decimal("30.00")

        item1 = MagicMock(spec=TransactionItem)
        item1.stylist_id = stylist_id
        item1.item_type = "service"
        item1.total_price = Decimal("200.00")
        item1.transaction_id = transaction_id

        item2 = MagicMock(spec=TransactionItem)
        item2.stylist_id = stylist_id
        item2.item_type = "product"
        item2.total_price = Decimal("50.00")
        item2.transaction_id = transaction_id

        class MockQuery:
            call_count = 0
            def filter(self, *args, **kwargs):
                return self
            def first(self):
                MockQuery.call_count += 1
                if MockQuery.call_count == 1:
                    return transaction
                return stylist
            def all(self):
                MockQuery.call_count += 1
                # Return items for TransactionItem query, empty for TipDistribution
                if MockQuery.call_count == 2:
                    return [item1, item2]
                return []
            def count(self):
                return 0

        db_session.query.return_value.filter.return_value = MockQuery()

        commissions = processor.calculate_commission(transaction_id)
        if isinstance(commissions, list):
            c = commissions[0]
        else:
            c = commissions

        assert c.service_earned == Decimal("90.00")
        assert c.retail_earned == Decimal("5.00")
        assert c.total_earned == Decimal("95.00")


class TestEdgeCases:
    def test_zero_amount_payment(self, processor, db_session):
        client = MagicMock(spec=Client)
        client.id = uuid4()
        client.total_visits = 0
        client.total_spent = Decimal("0.00")
        db_session.query.return_value.filter.return_value.first.return_value = client

        txn = processor.process_payment(
            client_id=client.id,
            processed_by=uuid4(),
            transaction_type="service",
            items=[{"item_type": "service", "item_name": "Free Consult", "unit_price": "0.00", "quantity": 1}],
        )
        assert txn.total == Decimal("0.00")
        assert txn.status == TransactionStatus.completed

    def test_refund_nonexistent_transaction(self, processor, db_session):
        db_session.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(PaymentError, match="Transaction not found"):
            processor.process_refund(
                transaction_id=uuid4(),
                processed_by=uuid4(),
                reason="Test",
            )

    def test_double_refund_prevented(self, processor, db_session):
        original = MagicMock(spec=Transaction)
        original.id = uuid4()
        original.total = Decimal("100.00")
        original.status = TransactionStatus.refunded

        db_session.query.return_value.filter.return_value.first.return_value = original

        with pytest.raises(PaymentError, match="already refunded"):
            processor.process_refund(
                transaction_id=original.id,
                processed_by=uuid4(),
                reason="Double refund test",
            )
