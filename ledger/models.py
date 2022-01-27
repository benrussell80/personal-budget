from typing import TypedDict
from django.db import models
from django.db.models import QuerySet
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from numbers import Number
import datetime

# Create your models here.
class OpeningBalanceDetail(TypedDict):
    account: 'Account'
    credit: Number
    debit: Number
    date: datetime.date
    notes: str | None


class Account(models.Model):
    class AccountKind(models.IntegerChoices):
        # ASSET - LIABILITY = EQUITY
        # every transaction should keep this equation balanced
        ASSET = 1       # e.g. car, house, cash
        LIABILITY = 2   # e.g. taxes payable, notes payable
        EQUITY = 3      # e.g. retained earnings, savings

        """
        Asset accounts: Record an increase with a debit and a decrease with a credit.

        Liability accounts: Record an increase with a credit and a decrease with a debit.

        Equity accounts: Record an increase to equity (revenues) with a credit and a decrease to equity (expenses) with a debit.
        """

    parent = models.ForeignKey('ledger.Account', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    key = models.TextField(unique=True)
    description = models.TextField()
    kind = models.SmallIntegerField(choices=AccountKind.choices)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    opening_date = models.DateField(auto_now_add=True)

    @property
    def balance(self):
        match self.kind:
            case Account.AccountKind.ASSET:
                total_expression = models.Sum(models.F('debit') - models.F('credit'))
            case Account.AccountKind.LIABILITY | Account.AccountKind.EQUITY:
                total_expression = models.Sum(models.F('credit') - models.F('debit'))
        
        return (
            Detail.objects.filter(account=self).aggregate(balance=total_expression)['balance'] or 0
        ) + self.opening_balance + sum([
            child.balance
            for child in self.children.iterator()
        ])

    def __str__(self) -> str:
        return f'{self.key} - {self.description}'

    def clean(self) -> None:
        if self.parent is not None and self.parent.kind != self.kind:
            raise ValidationError('Account must be of same kind as parent account.')

    def get_details(self) -> QuerySet['Detail']:
        return Detail.objects.filter(account=self).union(
            *[account.get_details() for account in self.children.all()]
        )

    def get_all_opening_balance_details(self) -> list[OpeningBalanceDetail]:
        records = [
            OpeningBalanceDetail(
                account=self,
                credit=0 if self.kind == Account.AccountKind.ASSET else self.opening_balance,
                debit=0 if self.kind != Account.AccountKind.ASSET else self.opening_balance,
                date=self.opening_date,
                notes='Opening Balance'
            )
        ]
        for child in self.children.iterator():
            records.extend(child.get_all_opening_balance_details())

        return records

    class Meta:
        ordering = ['key']


class Transaction(models.Model):
    date = models.DateField()
    notes = models.TextField(null=True, blank=True)

    def clean(self) -> None:
        asset = self.details.filter(account__kind=Account.AccountKind.ASSET).aggregate(total=models.Sum(models.F('debit') - models.F('credit')))['total'] or 0
        liability = self.details.filter(account__kind=Account.AccountKind.LIABILITY).aggregate(total=models.Sum(models.F('credit') - models.F('debit')))['total'] or 0
        equity = self.details.filter(account__kind=Account.AccountKind.EQUITY).aggregate(total=models.Sum(models.F('debit') - models.F('credit')))['total'] or 0
        if asset - liability != equity:
            raise ValidationError('Detail lines do not balance (i.e., ASSETS - LIABILITIES != EQUITIES).')

    def __str__(self) -> str:
        return f'Transaction(date={self.date}, details={self.details.count()}, notes={(self.notes or "")[:20]}...)'

class Detail(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='details')
    credit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    debit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transaction_details')
    notes = models.TextField(null=True, blank=True)

    def clean(self) -> None:
        if self.credit != 0 and self.debit != 0:
            raise ValidationError('Detail must be credit or debit; not both.')


class UserDefinedAttribute(models.Model):
    class AttributeKind(models.IntegerChoices):
        TEXT = 0
        NUMBER = 1
        ARRAY = 2
        CHOICE = 3
        DATE = 4
        
    name = models.TextField()
    kind = models.SmallIntegerField(choices=AttributeKind.choices)
    metadata = models.TextField(null=True, editable=False)

    def __str__(self) -> str:
        return self.name


class UserDefinedAttributeDetailThrough(models.Model):
    detail = models.ForeignKey(Detail, on_delete=models.CASCADE)
    attribute = models.ForeignKey(UserDefinedAttribute, on_delete=models.CASCADE)
    value = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['detail', 'attribute'],
                name='detail_attribute_unique_together'
            )
        ]


class QuickTransaction(models.Model):
    class ChargeKind(models.IntegerChoices):
        CREDIT = 1
        DEBIT = 2

    account_from = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='from_quick_charges')
    account_from_charge_kind = models.SmallIntegerField(choices=ChargeKind.choices)
    account_to = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='to_quick_charges')
    account_to_charge_kind = models.SmallIntegerField(choices=ChargeKind.choices)
    name = models.TextField()

    def clean(self) -> None:
        asset = int(self.account_from.kind == Account.AccountKind.ASSET) \
            * (-1 if self.account_from_charge_kind == QuickTransaction.ChargeKind.CREDIT else 1) \
            + int(self.account_to.kind == Account.AccountKind.ASSET) \
            * (-1 if self.account_to_charge_kind == QuickTransaction.ChargeKind.CREDIT else 1)

        liability = int(self.account_from.kind == Account.AccountKind.LIABILITY) \
            * (1 if self.account_from_charge_kind == QuickTransaction.ChargeKind.CREDIT else -1) \
            + int(self.account_to.kind == Account.AccountKind.LIABILITY) \
            * (1 if self.account_to_charge_kind == QuickTransaction.ChargeKind.CREDIT else -1)

        equity = int(self.account_from.kind == Account.AccountKind.EQUITY) \
            * (1 if self.account_from_charge_kind == QuickTransaction.ChargeKind.CREDIT else -1) \
            + int(self.account_to.kind == Account.AccountKind.EQUITY) \
            * (1 if self.account_to_charge_kind == QuickTransaction.ChargeKind.CREDIT else -1)

        if asset - liability != equity:
            raise ValidationError('Accounts do not balance (i.e. ASSETS - LIABILITIES != EQUITIES).')

    def __str__(self) -> str:
        return self.name