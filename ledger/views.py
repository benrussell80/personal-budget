import calendar
import datetime
from urllib.parse import urlencode

import pandas as pd
from bokeh.embed import components
from bokeh.models import ColumnDataSource, FactorRange
from bokeh.palettes import Category20
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.transform import factor_cmap
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (CreateAccount, CreateQuickTransaction,
                    CreateRecurringTransaction, ExpenseAnalyticsFilterForm,
                    SubmitQuickTransaction, TransactionDetailFormset,
                    TransactionForm)
from .models import (Account, Company, Detail, QuickTransaction, RecurringTransaction,
                     Transaction)


# Create your views here.
def index(request: HttpRequest) -> HttpResponse:
    companies = Company.objects.all()
    return render(request, 'ledger/index.html', {'companies': companies})


def company_index(request: HttpRequest, company_pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    root_accounts = Account.objects.filter(company=company, parent=None)  # .prefetch_related('children')
    return render(request, 'ledger/company_index.html', {'root_accounts': root_accounts, 'company': company})


# view to create quick transaction
def create_quick_transaction(request: HttpRequest, company_pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    if request.method == 'POST':
        form = CreateQuickTransaction(request.POST)
        if form.is_valid():
            try:
                instance: QuickTransaction = form.save(commit=False)
                instance.company = company
                instance.save()
                form.save_m2m()
            except Exception as e:
                messages.error(request, f'{e.__class__}: {e}')
            else:
                messages.success(request, 'Successfully created Quick Transaction.')
                return redirect(reverse('ledger:company_index', kwargs={'company_pk': company.pk}))
    else:
        form = CreateQuickTransaction()

    return render(request, 'ledger/create_quick_transaction.html', {'form': form, 'company': company})

# view to submit a quick transaction
def submit_quick_transaction(request: HttpRequest, company_pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    if request.method == 'POST':
        form = SubmitQuickTransaction(request.POST, company=company)
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    quick_transaction: QuickTransaction = form.cleaned_data['quick_transaction']
                    notes = form.cleaned_data.get('notes')

                    transaction = Transaction(
                        date=form.cleaned_data['date'],
                        notes=notes,
                        company=company,
                    )

                    from_detail = Detail(
                        transaction=transaction,
                        account=quick_transaction.account_from,
                        credit=0 if quick_transaction.account_from_charge_kind == QuickTransaction.ChargeKind.DEBIT else form.cleaned_data['amount'],
                        debit=0 if quick_transaction.account_from_charge_kind == QuickTransaction.ChargeKind.CREDIT else form.cleaned_data['amount'],
                        notes=notes,
                    )

                    to_detail = Detail(
                        transaction=transaction,
                        account=quick_transaction.account_to,
                        credit=0 if quick_transaction.account_to_charge_kind == QuickTransaction.ChargeKind.DEBIT else form.cleaned_data['amount'],
                        debit=0 if quick_transaction.account_to_charge_kind == QuickTransaction.ChargeKind.CREDIT else form.cleaned_data['amount'],
                        notes=notes,
                    )

                    transaction.save()
                    from_detail.save()
                    to_detail.save()
                    transaction.full_clean()
                    from_detail.full_clean()
                    to_detail.full_clean()
            except Exception as e:
                messages.error(request, 'Unable to submit quick transaction.')
            else:
                messages.success(request, 'Successfully created quick transaction.')
                return redirect(reverse('ledger:company_index', kwargs={'company_pk': company.pk}))
    else:
        form = SubmitQuickTransaction(company=company)

    return render(request, 'ledger/submit_quick_transaction.html', {'form': form, 'company': company})

# view to create an account
def create_account(request: HttpRequest, company_pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    if request.method == 'POST':
        form = CreateAccount(request.POST, company=company)
        if form.is_valid():
            try:
                instance: Account = form.save(commit=False)
                instance.company = company
                instance.save()
                form.save_m2m()
            except Exception as e:
                messages.error(request, f'{e.__class__}: {e}')
            else:
                messages.success(request, 'Successfully created account.')
                return redirect(reverse('ledger:company_index', kwargs={'company_pk': company.pk}))

    else:
        form = CreateAccount(company=company)

    return render(request, 'ledger/create_account.html', {'form': form, 'company': company})


# view individual account activity
def account_overview(request: HttpRequest, company_pk: int, pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    account = get_object_or_404(Account, pk=pk)
    if company != account.company:
        return HttpResponseBadRequest('That account does not belong to that company.')

    details = account.get_details()
    activity = [
        {
            'account': detail.account,
            'credit': detail.credit,
            'debit': detail.debit,
            'notes': detail.notes,
            'transaction': {
                'pk': detail.transaction_id,
                'date': detail.transaction.date
            }
        }
        for detail in details
    ]
    activity.extend(account.get_all_opening_balance_details())
    activity.sort(key=lambda record: record.get('date', record.get('transaction', {}).get('date')))
    balance = 0
    activity = [data | {
        'balance': (balance := (balance + data['credit'] - data['debit']) if account.kind != Account.AccountKind.ASSET else (balance + data['debit'] - data['credit']))
    } for data in activity]
    return render(request, 'ledger/account_overview.html', {'account': account, 'activity': activity, 'company': company})

# view transaction detail
def transaction_detail(request: HttpRequest, company_pk: int, pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    transaction = get_object_or_404(Transaction.objects.prefetch_related('details'), pk=pk)
    if company != transaction.company:
        return HttpResponseBadRequest('That transaction does not belong to that company.')
    
    return render(request, 'ledger/transaction_detail.html', {'transaction': transaction, 'company': company})

# view to submit a transaction
def submit_transaction(request: HttpRequest, company_pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    rec_trans_pk = request.GET.get('rec_trans_pk', None)
    rec_trans: RecurringTransaction | None
    if rec_trans_pk is not None:
        try:
            rec_trans = RecurringTransaction.objects.get(pk=int(rec_trans_pk))
        except:
            rec_trans = None
        else:
            if rec_trans is not None and rec_trans.transaction.company != company:
                return HttpResponseBadRequest('That recurring transaction does not belong to that company.')
    else:
        rec_trans = None

    if request.method == 'POST':
        transaction_form = TransactionForm(request.POST)
        formset = TransactionDetailFormset(request.POST)
        if transaction_form.is_valid() and formset.is_valid():
            try:
                with db_transaction.atomic():
                    transaction: Transaction = transaction_form.save(commit=False)
                    transaction.company = company
                    transaction.save()
                    transaction_form.save_m2m()
                    formset.instance = transaction
                    formset.save()
                    try:
                        transaction.full_clean()
                    except ValidationError as e:
                        transaction_form.add_error(None, e)
                        raise
            except Exception as e:
                messages.error(request, 'Unable to save transaction.')
            else:
                messages.success(request, 'Successfully posted transaction.')
                return redirect(reverse('ledger:company_index', kwargs={'company_pk': company.pk}))
    else:
        if rec_trans is not None:
            transaction_form = TransactionForm(initial={
                'notes': rec_trans.transaction.notes
            })
            formset = TransactionDetailFormset(initial=[
                {
                    'debit': detail.debit,
                    'credit': detail.credit,
                    'account': detail.account,
                    'notes': detail.notes
                }
                for detail in rec_trans.transaction.details.iterator()
            ])
            formset.extra = min(formset.extra, rec_trans.transaction.details.count() - formset.min_num)
        else:
            transaction_form = TransactionForm()
            formset = TransactionDetailFormset()
    
    return render(request, 'ledger/submit_transaction.html', {'transaction_form': transaction_form, 'formset': formset, 'company': company})


def create_rec_trans(request: HttpRequest, company_pk: int, pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    transaction = get_object_or_404(Transaction.objects.prefetch_related('details'), pk=pk)
    if company != transaction.company:
        return HttpResponseBadRequest('That transaction does not belong to that company.')
    
    if request.method == 'POST':
        form = CreateRecurringTransaction(request.POST)
        if form.is_valid():
            form.instance.transaction = transaction
            try:
                form.save()
            except Exception as e:
                messages.error(request, f'Unable to create recurring transaction: {e.__class__.__name__}{str(e)}')
            else:
                messages.success(request, 'Successfully created recurring transaction.')
                return redirect(reverse('ledger:company_index', kwargs={'company_pk': company.pk}))
    else:
        form = CreateRecurringTransaction()
    
    return render(request, 'ledger/create_rec_trans.html', {'form': form, 'transaction': transaction, 'company': company})


def list_rec_trans(request: HttpRequest, company_pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    recs = RecurringTransaction.objects.filter(transaction__company=company)
    return render(request, 'ledger/list_rec_trans.html', {'recs': recs, 'company': company})


def tax_calculator(request: HttpRequest) -> HttpResponse:
    return render(request, 'ledger/tax_calculator.html')
