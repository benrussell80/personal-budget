from django import forms

from .models import Company, Detail, QuickTransaction, Account, RecurringTransaction, RecurringTransactionDetail, Transaction

# form to create a quick transaction
class CreateQuickTransaction(forms.ModelForm):
    class Meta:
        model = QuickTransaction
        exclude = [
            'company',
        ]
        widgets = {
            'name': forms.TextInput()
        }

    def __init__(self, *args, company: Company, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['account_from'].queryset = Account.objects.filter(company=company, is_leaf=True)
        self.fields['account_to'].queryset = Account.objects.filter(company=company, is_leaf=True)


# form to submit a quick transaction
class SubmitQuickTransaction(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    quick_transaction = forms.ModelChoiceField(None)
    amount = forms.DecimalField(decimal_places=2, max_digits=12, min_value=0)
    notes = forms.CharField(widget=forms.Textarea(), required=False)

    def __init__(self, *args, company: Company, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quick_transaction'].queryset = QuickTransaction.objects.filter(company=company)

# form to submit a transaction
class DetailForm(forms.ModelForm):
    class Meta:
        model = Detail
        fields = [
            'account',
            'credit',
            'debit',
            'notes'
        ]
        widgets = {
            'notes': forms.TextInput()
        }

    def __init__(self, *args, company: Company, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = Account.objects.filter(company=company, is_leaf=True)


TransactionDetailFormset = forms.inlineformset_factory(
    parent_model=Transaction,
    model=Detail,
    form=DetailForm,
    extra=10,
    exclude=[],
    can_delete=True,
    min_num=2,
)


class RecurringTransactionDetailForm(forms.ModelForm):
    class Meta:
        model = RecurringTransactionDetail
        fields = [
            'account',
            'credit',
            'debit',
            'notes',
        ]
        widgets = {
            'notes': forms.TextInput()
        }


RecurringTransactionDetailFormset = forms.inlineformset_factory(
    parent_model=RecurringTransaction,
    model=RecurringTransactionDetail,
    form=RecurringTransactionDetailForm,
    extra=10,
    exclude=[],
    can_delete=True,
    min_num=2,
)


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        exclude = [
            'company',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }


class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        exclude = [
            'company',
        ]
        widgets = {
            'name': forms.TextInput()
        }


class CreateAccount(forms.ModelForm):
    class Meta:
        exclude = [
            'company',
        ]
        model = Account
        widgets = {
            'key': forms.TextInput(),
            'description': forms.TextInput()
        }

    def __init__(self, *args, company: Company, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Account.objects.filter(is_leaf=False, company=company)


class CreateRecurringTransaction(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = ['name']
        widgets = {
            'name': forms.TextInput()
        }


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        exclude = []
        widgets = {
            'name': forms.TextInput()
        }
