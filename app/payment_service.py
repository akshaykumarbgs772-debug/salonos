from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    Client, Commission, GiftCard, TipDistribution,
    Transaction, TransactionItem, TransactionStatus,
    TransactionType, User,
)


class PaymentError(Exception):
    pass


class PaymentProcessor:
    def __init__(self, db: Session):
        self.db = db

    def calculate_totals(
        self,
        items: List[dict],
        tip_amount: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        tax_rate: Decimal = Decimal("0.00"),
    ) -> dict:
        subtotal = Decimal("0.00")
        for item in items:
            qty = Decimal(str(item.get("quantity", 1)))
            price = Decimal(str(item["unit_price"]))
            subtotal += qty * price

        tax_amount = (subtotal * Decimal(str(tax_rate)) / Decimal("100")).quantize(Decimal("0.01"))
        discount = Decimal(str(discount_amount))
        tip = Decimal(str(tip_amount))
        total = (subtotal + tax_amount + tip - discount).quantize(Decimal("0.01"))

        return {
            "subtotal": subtotal.quantize(Decimal("0.01")),
            "tax_amount": tax_amount,
            "tip_amount": tip.quantize(Decimal("0.01")),
            "discount_amount": discount.quantize(Decimal("0.01")),
            "total": max(total, Decimal("0.00")),
        }

    def process_payment(
        self,
        client_id: UUID,
        processed_by: UUID,
        transaction_type: str,
        items: List[dict],
        payment_method: str = "cash",
        tip_amount: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        card_last_four: Optional[str] = None,
        appointment_id: Optional[UUID] = None,
        gift_card_code: Optional[str] = None,
        gift_card_amount: Optional[Decimal] = None,
        tip_split: Optional[List[dict]] = None,
        notes: Optional[str] = None,
    ) -> Transaction:
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise PaymentError("Client not found")

        totals = self.calculate_totals(items, tip_amount, discount_amount)

        if gift_card_code and gift_card_amount:
            gift_card = self.db.query(GiftCard).filter(
                GiftCard.code == gift_card_code,
                GiftCard.is_active == True,
            ).first()
            if not gift_card:
                raise PaymentError("Invalid gift card")
            if gift_card.current_balance < gift_card_amount:
                raise PaymentError("Insufficient gift card balance")
            gift_card.current_balance -= gift_card_amount
            if gift_card.current_balance <= Decimal("0.00"):
                gift_card.is_active = False

        transaction = Transaction(
            client_id=client_id,
            processed_by=processed_by,
            appointment_id=appointment_id,
            transaction_type=TransactionType(transaction_type),
            status=TransactionStatus.completed,
            subtotal=totals["subtotal"],
            tax_amount=totals["tax_amount"],
            tip_amount=totals["tip_amount"],
            discount_amount=totals["discount_amount"],
            total=totals["total"],
            payment_method=payment_method,
            card_last_four=card_last_four,
            notes=notes,
        )
        self.db.add(transaction)
        self.db.flush()

        for item_data in items:
            line_item = TransactionItem(
                transaction_id=transaction.id,
                item_type=item_data.get("item_type", "service"),
                item_id=item_data.get("item_id"),
                item_name=item_data["item_name"],
                quantity=item_data.get("quantity", 1),
                unit_price=Decimal(str(item_data["unit_price"])),
                total_price=Decimal(str(item_data["unit_price"])) * Decimal(str(item_data.get("quantity", 1))),
                stylist_id=item_data.get("stylist_id"),
            )
            self.db.add(line_item)

        total_tip = Decimal(str(tip_amount))
        if total_tip > 0 and tip_split:
            for split in tip_split:
                stylist_id = UUID(split["stylist_id"]) if isinstance(split["stylist_id"], str) else split["stylist_id"]
                pct = Decimal(str(split.get("percentage", 0)))
                split_amount = (total_tip * pct / Decimal("100")).quantize(Decimal("0.01"))
                td = TipDistribution(
                    transaction_id=transaction.id,
                    stylist_id=stylist_id,
                    amount=split_amount,
                    percentage=pct,
                )
                self.db.add(td)
        elif total_tip > 0 and not tip_split:
            service_stylist_id = None
            for item_data in items:
                if item_data.get("stylist_id"):
                    service_stylist_id = item_data["stylist_id"]
                    break
            if service_stylist_id:
                td = TipDistribution(
                    transaction_id=transaction.id,
                    stylist_id=service_stylist_id,
                    amount=Decimal(str(tip_amount)),
                    percentage=Decimal("100.00"),
                )
                self.db.add(td)

        client.total_visits += 1
        client.total_spent = (client.total_spent or Decimal("0.00")) + totals["total"]
        client.last_visit_at = transaction.created_at

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def process_refund(
        self,
        transaction_id: UUID,
        processed_by: UUID,
        amount: Optional[Decimal] = None,
        reason: str = "",
    ) -> Transaction:
        original = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not original:
            raise PaymentError("Transaction not found")
        if original.status == TransactionStatus.refunded:
            raise PaymentError("Transaction already refunded")

        refund_amount = amount if amount else original.total
        if refund_amount > original.total:
            raise PaymentError("Refund amount exceeds transaction total")

        refund = Transaction(
            appointment_id=original.appointment_id,
            client_id=original.client_id,
            processed_by=processed_by,
            transaction_type=TransactionType.refund,
            status=TransactionStatus.completed,
            subtotal=-original.subtotal,
            tax_amount=-original.tax_amount,
            tip_amount=-original.tip_amount,
            discount_amount=Decimal("0.00"),
            total=-refund_amount,
            payment_method=original.payment_method,
            refund_of_id=original.id,
            refund_reason=reason,
        )
        self.db.add(refund)

        if refund_amount >= original.total:
            original.status = TransactionStatus.refunded
        else:
            original.status = TransactionStatus.partial_refund

        self.db.commit()
        self.db.refresh(refund)
        return refund

    def distribute_tips(self, transaction_id: UUID, splits: List[dict]) -> List[TipDistribution]:
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise PaymentError("Transaction not found")
        if transaction.tip_amount <= Decimal("0.00"):
            raise PaymentError("No tips to distribute")

        existing = self.db.query(TipDistribution).filter(
            TipDistribution.transaction_id == transaction_id
        ).count()
        if existing > 0:
            raise PaymentError("Tips already distributed")

        distributions = []
        for split in splits:
            stylist_id = UUID(split["stylist_id"]) if isinstance(split["stylist_id"], str) else split["stylist_id"]
            pct = Decimal(str(split.get("percentage", 0)))
            amount = (transaction.tip_amount * pct / Decimal("100")).quantize(Decimal("0.01"))

            td = TipDistribution(
                transaction_id=transaction_id,
                stylist_id=stylist_id,
                amount=amount,
                percentage=pct,
            )
            self.db.add(td)
            distributions.append(td)

        self.db.commit()
        return distributions

    def calculate_commission(self, transaction_id: UUID) -> Commission:
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise PaymentError("Transaction not found")

        items = self.db.query(TransactionItem).filter(
            TransactionItem.transaction_id == transaction_id
        ).all()

        stylist_earnings = {}
        for item in items:
            if not item.stylist_id:
                continue
            sid = item.stylist_id
            if sid not in stylist_earnings:
                stylist = self.db.query(User).filter(User.id == sid).first()
                if not stylist:
                    continue
                rate = stylist.commission_rate or Decimal("40.00")
                stylist_earnings[sid] = {
                    "rate": rate,
                    "service_amount": Decimal("0.00"),
                    "retail_amount": Decimal("0.00"),
                    "tip_amount": Decimal("0.00"),
                }

            price = item.total_price
            if item.item_type == "service":
                stylist_earnings[sid]["service_amount"] += price
            elif item.item_type == "product":
                stylist_earnings[sid]["retail_amount"] += price

        tips = self.db.query(TipDistribution).filter(
            TipDistribution.transaction_id == transaction_id
        ).all()
        for tip in tips:
            sid = tip.stylist_id
            if sid in stylist_earnings:
                stylist_earnings[sid]["tip_amount"] += tip.amount

        commissions = []
        for stylist_id, data in stylist_earnings.items():
            service_earned = (data["service_amount"] * data["rate"] / Decimal("100")).quantize(Decimal("0.01"))
            retail_rate = Decimal("10.00")
            retail_earned = (data["retail_amount"] * retail_rate / Decimal("100")).quantize(Decimal("0.01"))
            tip_earned = data["tip_amount"]

            total_earned = (service_earned + retail_earned + tip_earned).quantize(Decimal("0.01"))

            commission = Commission(
                stylist_id=stylist_id,
                transaction_id=transaction_id,
                appointment_id=transaction.appointment_id,
                service_amount=data["service_amount"],
                retail_amount=data["retail_amount"],
                tip_amount=data["tip_amount"],
                service_rate=data["rate"],
                retail_rate=retail_rate,
                service_earned=service_earned,
                retail_earned=retail_earned,
                tip_earned=tip_earned,
                total_earned=total_earned,
            )
            self.db.add(commission)
            commissions.append(commission)

        self.db.commit()
        for c in commissions:
            self.db.refresh(c)
        return commissions[0] if len(commissions) == 1 else commissions

    def redeem_gift_card(self, code: str, amount: Decimal) -> GiftCard:
        card = self.db.query(GiftCard).filter(
            GiftCard.code == code,
            GiftCard.is_active == True,
        ).first()
        if not card:
            raise PaymentError("Gift card not found or inactive")
        if card.current_balance < amount:
            raise PaymentError(f"Insufficient balance: ₹{card.current_balance:.2f} available")
        if card.expires_at and card.expires_at < __import__("datetime").date.today():
            raise PaymentError("Gift card has expired")

        card.current_balance -= amount
        if card.current_balance <= Decimal("0.00"):
            card.is_active = False
        self.db.commit()
        self.db.refresh(card)
        return card

    def issue_gift_card(
        self,
        initial_balance: Decimal,
        client_id: Optional[UUID] = None,
        expires_at: Optional[date] = None,
    ) -> GiftCard:
        import uuid
        code = f"SALON-{uuid.uuid4().hex[:8].upper()}"
        card = GiftCard(
            code=code,
            client_id=client_id,
            original_balance=initial_balance,
            current_balance=initial_balance,
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        return card
