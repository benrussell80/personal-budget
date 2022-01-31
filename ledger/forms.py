from django import forms

from .models import Detail, QuickTransaction, Account, RecurringTransaction, Transaction

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
    can_delete=True,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Account.objects.filter(is_leaf=False)


class MonthField(forms.DateField):
    widget = forms.DateInput(attrs={'type': 'month'})
    input_formats = ['%Y-%m', '%m/%Y']


class ExpenseAnalyticsFilterForm(forms.Form):
    start_month = MonthField()
    end_month = MonthField()
    accounts = forms.ModelMultipleChoiceField(Account.objects)


class CreateRecurringTransaction(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = ['name']
        widgets = {
            'name': forms.TextInput()
        }
