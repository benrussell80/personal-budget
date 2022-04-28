from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (CompanyForm, CreateAccount, CreateQuickTransaction,
                    CreateRecurringTransaction, RecurringTransactionDetailFormset, RecurringTransactionForm, SubmitQuickTransaction,
                    TransactionDetailFormset, TransactionForm)
from .models import (Account, Company, Detail, QuickTransaction,
                     RecurringTransaction, RecurringTransactionDetail,
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
        form = CreateQuickTransaction(request.POST, company=company)
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
        form = CreateQuickTransaction(company=company)

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
            if rec_trans is not None and rec_trans.company != company:
                return HttpResponseBadRequest('That recurring transaction does not belong to that company.')
    else:
        rec_trans = None

    if request.method == 'POST':
        transaction_form = TransactionForm(request.POST)
        formset = TransactionDetailFormset(request.POST, form_kwargs={'company': company})
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
                'notes': rec_trans.notes
            })
            formset = TransactionDetailFormset(initial=[
                {
                    'debit': detail.debit,
                    'credit': detail.credit,
                    'account': detail.account,
                    'notes': detail.notes
                }
                for detail in rec_trans.details.iterator()
            ], form_kwargs={'company': company})
            formset.extra = min(formset.extra, rec_trans.details.count() - formset.min_num)
        else:
            transaction_form = TransactionForm()
            formset = TransactionDetailFormset(form_kwargs={'company': company})
    
    return render(request, 'ledger/submit_transaction.html', {'transaction_form': transaction_form, 'formset': formset, 'company': company})


def create_rec_trans(request: HttpRequest, company_pk: int, pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    transaction = get_object_or_404(Transaction.objects.prefetch_related('details'), pk=pk)
    if company != transaction.company:
        return HttpResponseBadRequest('That transaction does not belong to that company.')
    
    if request.method == 'POST':
        form = CreateRecurringTransaction(request.POST)
        if form.is_valid():
            try:
                form.instance.company = company
                form.instance.notes = transaction.notes
                with db_transaction.atomic():
                    rec_trans = form.save()
                    RecurringTransactionDetail.objects.bulk_create([
                        RecurringTransactionDetail(
                            parent=rec_trans,
                            credit=detail.credit,
                            debit=detail.debit,
                            account=detail.account,
                            notes=detail.notes,
                        )
                        for detail in transaction.details.iterator()
                    ])
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
    recs = RecurringTransaction.objects.filter(company=company)
    return render(request, 'ledger/list_rec_trans.html', {'recs': recs, 'company': company})


def tax_calculator(request: HttpRequest) -> HttpResponse:
    return render(request, 'ledger/tax_calculator.html')


def edit_transaction(request: HttpRequest, company_pk: int, transaction_pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    transaction = get_object_or_404(Transaction, pk=transaction_pk)
    if transaction.company != company:
        return HttpResponseBadRequest('That transaction does not belong to that company.')

    if request.method == 'POST':
        transaction_form = TransactionForm(request.POST, instance=transaction)
        formset = TransactionDetailFormset(request.POST, instance=transaction, form_kwargs={'company': company})
        if transaction_form.is_valid() and formset.is_valid():
            try:
                with db_transaction.atomic():
                    transaction_form.save()
                    formset.save()
                    try:
                        transaction.full_clean()
                    except ValidationError as e:
                        transaction_form.add_error(None, e)
                        raise
            except Exception as e:
                messages.error(request, 'Unable to save transaction.')
            else:
                messages.success(request, 'Successfully updated transaction.')
                return redirect(reverse('ledger:company_index', kwargs={'company_pk': company.pk}))

    else:
        transaction_form = TransactionForm(instance=transaction)
        formset = TransactionDetailFormset(instance=transaction, form_kwargs={'company': company})

    return render(request, 'ledger/edit_transaction.html', {'company': company, 'transaction_form': transaction_form, 'formset': formset})


def edit_recurring_transaction(request: HttpRequest, company_pk: int, rec_trans_pk: int) -> HttpResponse:
    company = get_object_or_404(Company, pk=company_pk)
    rec_trans = get_object_or_404(RecurringTransaction, pk=rec_trans_pk)
    if rec_trans.company != company:
        return HttpResponseBadRequest('That recurring transaction does not belong to that company.')

    if request.method == 'POST':
        transaction_form = RecurringTransactionForm(request.POST, instance=rec_trans)
        formset = RecurringTransactionDetailFormset(request.POST, instance=rec_trans)
        if transaction_form.is_valid() and formset.is_valid():
            try:
                with db_transaction.atomic():
                    transaction_form.save()
                    formset.save()
                    try:
                        rec_trans.full_clean()
                    except ValidationError as e:
                        transaction_form.add_error(None, e)
                        raise
            except Exception as e:
                messages.error(request, 'Unable to save rec_trans.')
            else:
                messages.success(request, 'Successfully updated rec_trans.')
                return redirect(reverse('ledger:company_index', kwargs={'company_pk': company.pk}))

    else:
        transaction_form = RecurringTransactionForm(instance=rec_trans)
        formset = RecurringTransactionDetailFormset(instance=rec_trans)

    return render(request, 'ledger/edit_recurring_transaction.html', {'company': company, 'transaction_form': transaction_form, 'formset': formset})


def create_company(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save()
            return redirect(reverse('ledger:company_index', kwargs={'company_pk': company.pk}))
    else:
        form = CompanyForm()

    return render(request, 'ledger/create_company.html', {'form': form})
