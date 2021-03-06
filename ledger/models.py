from decimal import Decimal
from typing import Any
from django.db import models
from django.db.models import QuerySet
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

# Create your models here.
class Company(models.Model):
    class Meta:
        verbose_name_plural = 'companies'

    name = models.TextField(unique=True)

    def __str__(self) -> str:
        return self.name


class AccountModelManager(models.Manager):
    def get_queryset(self) -> QuerySet['Account']:
        return super().get_queryset().prefetch_related('children', 'transaction_details')


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

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accounts')
    parent = models.ForeignKey('ledger.Account', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    key = models.TextField()
    description = models.TextField()
    kind = models.SmallIntegerField(choices=AccountKind.choices)
    opening_date = models.DateField(auto_now_add=True)
    is_leaf = models.BooleanField(default=False)

    @property
    def balance(self):
        match self.kind:
            case Account.AccountKind.ASSET:
                total_expression = models.Sum(models.F('debit') - models.F('credit'))
            case Account.AccountKind.LIABILITY | Account.AccountKind.EQUITY:
                total_expression = models.Sum(models.F('credit') - models.F('debit'))
        
        return (
            self.transaction_details.aggregate(balance=total_expression)['balance'] or 0
        ) + sum([
            child.balance
            for child in self.children.iterator()
        ])

    objects = AccountModelManager()

    def __str__(self) -> str:
        return f'{self.key} - {self.description}'

    def clean(self) -> None:
        if self.parent is not None and self.parent.kind != self.kind:
            raise ValidationError('Account must be of same kind as parent account.')

    def get_details(self) -> QuerySet['Detail']:
        return Detail.objects.filter(account=self).union(
            *[account.get_details() for account in self.children.all()]
        )

    def get_all_opening_balance_details(self) -> list[dict[str, Any]]:
        records = []
        
        for child in self.children.iterator():
            records.extend(child.get_all_opening_balance_details())

        return records

    class Meta:
        ordering = ['key']
        constraints = [
            models.UniqueConstraint(
                fields=['key', 'company'],
                name='account_key_unique_for_company',
            )
        ]


class Transaction(models.Model):
    date = models.DateField()
    notes = models.TextField(null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions')

    def clean(self) -> None:
        assets = Decimal(0)
        liabilities = Decimal(0)
        equities = Decimal(0)
        for detail in self.details.iterator():
            if detail.account.company != self.company:
                raise ValidationError('All detail lines must use accounts from the same company.')
            
            match detail.account.kind:
                case Account.AccountKind.ASSET:
                    assets += detail.debit - detail.credit
                case Account.AccountKind.LIABILITY:
                    liabilities += detail.credit - detail.debit
                case Account.AccountKind.EQUITY:
                    equities += detail.credit - detail.debit
        
        if assets - liabilities != equities:
            raise ValidationError(f'Detail lines do not balance (i.e., ASSETS({assets}) - LIABILITIES({liabilities}) != EQUITIES({equities})).')

    def __str__(self) -> str:
        return f'Transaction(date={self.date}, details={self.details.count()}, notes={(self.notes or "")[:20]}...)'


class DetailManager(models.Manager):
    def get_queryset(self) -> QuerySet['Detail']:
        return super().get_queryset().select_related('transaction')


class Detail(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='details')
    credit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    debit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transaction_details')
    notes = models.TextField(null=True, blank=True)

    def clean(self) -> None:
        if self.credit != 0 and self.debit != 0:
            raise ValidationError('Detail must be credit or debit; not both.')

    objects = DetailManager()


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
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='udf_attributes')

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

    def clean(self) -> None:
        if self.detail.account.company != self.attribute.company:
            raise ValidationError('Detail must be from same company as attribute.')


class QuickTransaction(models.Model):
    class ChargeKind(models.IntegerChoices):
        CREDIT = 1
        DEBIT = 2

    account_from = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='from_quick_charges')
    account_from_charge_kind = models.SmallIntegerField(choices=ChargeKind.choices)
    account_to = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='to_quick_charges')
    account_to_charge_kind = models.SmallIntegerField(choices=ChargeKind.choices)
    name = models.TextField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='quick_transactions')

    def clean(self) -> None:
        if self.account_from.company != self.company or self.account_to.company != self.company:
            raise ValidationError('To and From accounts must belong to the same company.')
        
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


class RecurringTransaction(models.Model):
    name = models.TextField()
    company = models.ForeignKey(Company, models.CASCADE, related_name='recurring_transactions')
    notes = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        # all detail accounts must be in company
        Transaction.clean(self)


class RecurringTransactionDetail(models.Model):
    parent = models.ForeignKey(RecurringTransaction, models.CASCADE, related_name='details')
    credit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    debit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='recurring_transaction_details')
    notes = models.TextField(null=True, blank=True)

    def clean(self) -> None:
        if self.credit != 0 and self.debit != 0:
            raise ValidationError('Detail must be credit or debit; not both.')
