from django import forms

from .models import Detail, QuickTransaction, Account, Transaction

# form to create a quick transaction
class CreateQuickTransaction(forms.ModelForm):
    class Meta:
        model = QuickTransaction
        exclude = []
        widgets = {
            'name': forms.TextInput()
        }


# form to submit a quick transaction
class SubmitQuickTransaction(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    quick_transaction = forms.ModelChoiceField(QuickTransaction.objects)
    amount = forms.DecimalField(decimal_places=2, max_digits=12, min_value=0)
    notes = forms.CharField(widget=forms.Textarea(), required=False)


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


TransactionDetailFormset = forms.inlineformset_factory(
    parent_model=Transaction,
    model=Detail,
    form=DetailForm,
    extra=10,
    exclude=[],
    can_delete=False,
    min_num=2,
)


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        exclude = []
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }


class CreateAccount(forms.ModelForm):
    class Meta:
        exclude = []
        model = Account
        widgets = {
            'key': forms.TextInput(),
            'description': forms.TextInput()
        }


class ExpenseAnalyticsFilterForm(forms.Form):
    start_month = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_month = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    accounts = forms.ModelMultipleChoiceField(Account.objects)
    