from django.core.exceptions import ValidationError
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.urls import reverse
from .models import Account, QuickTransaction, Transaction, Detail
from .forms import CreateAccount, CreateQuickTransaction, SubmitQuickTransaction, TransactionDetailFormset, TransactionForm
from django.db import transaction as db_transaction
from django.db import reset_queries, connection
from django.utils.timezone import now

# Create your views here.
def index(request: HttpRequest):
    root_accounts = Account.objects.filter(parent=None).prefetch_related('children')
    return render(request, 'ledger/index.html', {'root_accounts': root_accounts})


# view to create quick transaction
def create_quick_transaction(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CreateQuickTransaction(request.POST)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                messages.error(request, f'{e.__class__}: {e}')
            else:
                messages.success(request, 'Successfull created Quick Transaction.')
                return redirect(reverse('ledger:index'))
    else:
        form = CreateQuickTransaction()

    return render(request, 'ledger/create_quick_transaction.html', {'form': form})

# view to submit a quick transaction
def submit_quick_transaction(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = SubmitQuickTransaction(request.POST)
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    quick_transaction: QuickTransaction = form.cleaned_data['quick_transaction']

                    transaction = Transaction(
                        date=form.cleaned_data['date'],
                        notes=form.cleaned_data.get('notes')
                    )

                    from_detail = Detail(
                        transaction=transaction,
                        account=quick_transaction.account_from,
                        credit=0 if quick_transaction.account_from_charge_kind == QuickTransaction.ChargeKind.DEBIT else form.cleaned_data['amount'],
                        debit=0 if quick_transaction.account_from_charge_kind == QuickTransaction.ChargeKind.CREDIT else form.cleaned_data['amount'],
                    )

                    to_detail = Detail(
                        transaction=transaction,
                        account=quick_transaction.account_to,
                        credit=0 if quick_transaction.account_to_charge_kind == QuickTransaction.ChargeKind.DEBIT else form.cleaned_data['amount'],
                        debit=0 if quick_transaction.account_to_charge_kind == QuickTransaction.ChargeKind.CREDIT else form.cleaned_data['amount'],
                    )

                    transaction.save()
                    from_detail.save()
                    to_detail.save()
            except Exception as e:
                print(traceback.format_exc())
                messages.error(request, 'Unable to submit quick transaction.')
            else:
                messages.success(request, 'Successfully created quick transaction.')
                return redirect(reverse('ledger:index'))
    else:
        form = SubmitQuickTransaction()

    return render(request, 'ledger/submit_quick_transaction.html', {'form': form})

# view to create an account
def create_account(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CreateAccount(request.POST)
        if form.is_valid():
            try:
                form.save()
            except Exception as e:
                messages.error(request, f'{e.__class__}: {e}')
            else:
                messages.success(request, 'Successfully created account.')
                return redirect(reverse('ledger:index'))

    else:
        form = CreateAccount()

    return render(request, 'ledger/create_account.html', {'form': form})

# view to see the general ledger (as a table)
# view other reports (income statement, balance sheet)
# view graphs

# view individual account activity
def account_overview(request: HttpRequest, pk: int) -> HttpResponse:
    account = get_object_or_404(Account, pk=pk)
    details = account.get_details()
    return render(request, 'ledger/account_overview.html', {'account': account, 'activity': details})

# view transaction detail
def transaction_detail(request: HttpRequest, pk: int) -> HttpResponse:
    transaction = get_object_or_404(Transaction.objects.prefetch_related('details'), pk=pk)
    return render(request, 'ledger/transaction_detail.html', {'transaction': transaction})

# view to submit a transaction
def submit_transaction(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        transaction_form = TransactionForm(request.POST)
        formset = TransactionDetailFormset(request.POST)
        if transaction_form.is_valid() and formset.is_valid():
            try:
                with db_transaction.atomic():
                    transaction = transaction_form.save()
                    formset.instance = transaction
                    formset.save()
                    try:
                        transaction.full_clean()
                    except ValidationError as e:
                        transaction_form.add_error(None, e)
                        raise
            except:
                pass
            else:
                return redirect(reverse('ledger:index'))
        else:
            print(transaction_form.errors)
            print(formset.errors)
    else:
        transaction_form = TransactionForm()
        formset = TransactionDetailFormset()
    
    return render(request, 'ledger/submit_transaction.html', {'transaction_form': transaction_form, 'formset': formset})