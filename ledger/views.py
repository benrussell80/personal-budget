from urllib.parse import urlencode
from bokeh.resources import INLINE
import calendar
from django.db.models import QuerySet
import datetime
from bokeh.embed import components
from bokeh.models import ColumnDataSource, FactorRange, Panel, Tabs, DataTable, TableColumn
from bokeh.transform import factor_cmap
from bokeh.palettes import Category20
from bokeh.plotting import figure
import pandas as pd
from django.core.exceptions import ValidationError
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.urls import reverse
from .models import Account, QuickTransaction, Transaction, Detail
from .forms import CreateAccount, CreateQuickTransaction, ExpenseAnalyticsFilterForm, SubmitQuickTransaction, TransactionDetailFormset, TransactionForm
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
                    notes = form.cleaned_data.get('notes')

                    transaction = Transaction(
                        date=form.cleaned_data['date'],
                        notes=notes
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

# view to see reports (balance sheet, income statement, statement of cash flows)
# view other reports (income statement, balance sheet)

# view graphs
def expense_analytics(request: HttpRequest) -> HttpResponse:
    accounts = request.GET.getlist('accounts', [])
    start_month = request.GET.get('start_month')
    end_month = request.GET.get('end_month')
    try:
        accounts = list(map(int, accounts))
        if start_month is None or end_month is None:
            raise ValueError('Must pass start_month and end_month.')
        start_month = datetime.datetime.strptime(start_month, '%Y-%m')
        end_month = datetime.datetime.strptime(end_month, '%Y-%m')
        end_month = end_month.replace(day=calendar.monthrange(end_month.year, end_month.month)[1], minute=59, hour=23, second=59)
    except:
        messages.error(request, 'Invalid parameters received.')
        return redirect(reverse('ledger:index'))

    # plot amount paid for expenses grouped by month, kind
    # DataFrame with columns [Account, Month, Amount]
    accounts: QuerySet[Account] = Account.objects.filter(pk__in=accounts).iterator()
    dfs = []
    for acct in accounts:
        details = acct.get_details().values_list('transaction__date', 'credit', 'debit')
        df = pd.DataFrame(details, columns=['date', 'credit', 'debit'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.loc[
            (df['date']>=start_month)
            &(df['date']<=end_month)
        ]
        match acct.kind:
            case Account.AccountKind.ASSET:
                df['amount'] = df['debit'] - df['credit']
            case Account.AccountKind.LIABILITY | Account.AccountKind.EQUITY:
                df['amount'] = df['credit'] - df['debit']
        
        df.drop(columns=['credit', 'debit'], inplace=True)
        df['month'] = df['date'].apply(lambda value: value.strftime('%Y-%m'))
        df = df.groupby(
            'month',
            as_index=False
        ).agg(
            amount=pd.NamedAgg(column='amount', aggfunc='sum')
        )
        df['account'] = str(acct)
        dfs.append(df)

    data: pd.DataFrame = pd.concat(dfs, ignore_index=True)
    x = data.apply(lambda row: (row['account'], row['month']), axis=1).to_list()

    x_range = FactorRange(*x)
    months = data['month'].drop_duplicates().sort_values().to_list()
    palette = Category20[max(len(months), 3)]

    source = ColumnDataSource({
        'x': x,
        'amount': data['amount']
    })

    plot = figure(
        x_range=x_range
    )
    plot.vbar(
        x='x',
        top='amount',
        source=source,
        line_color='white',
        fill_color=factor_cmap('x', factors=months, palette=palette)
    )
    script, div = components(plot)
    return render(request, 'ledger/expense_analytics.html', {'script': script, 'div': div, 'INLINE': INLINE.render()})


def expense_analytics_filter(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = ExpenseAnalyticsFilterForm(request.POST)
        if form.is_valid():
            start_month = form.cleaned_data['start_month']
            end_month = form.cleaned_data['end_month']
            accounts = form.cleaned_data['accounts']
            params = [
                ('start_month', start_month.strftime('%Y-%m')),
                ('end_month', end_month.strftime('%Y-%m')),
                *[
                    ('accounts', pk)
                    for pk in accounts.values_list('pk', flat=True)
                ]
            ]
            return redirect(reverse('ledger:expense_analytics') + '?' + urlencode(params))
    else:
        form = ExpenseAnalyticsFilterForm()

    return render(request, 'ledger/expense_analytics_filter.html', {'form': form})


def analytics(request: HttpRequest) -> HttpResponse:
    return render(request, 'ledger/analytics.html')


# view individual account activity
def account_overview(request: HttpRequest, pk: int) -> HttpResponse:
    account = get_object_or_404(Account, pk=pk)
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
    return render(request, 'ledger/account_overview.html', {'account': account, 'activity': activity})

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
                messages.error(request, 'Unable to save transaction.')
            else:
                messages.success(request, 'Successfully posted transaction.')
                return redirect(reverse('ledger:index'))
    else:
        transaction_form = TransactionForm()
        formset = TransactionDetailFormset()
    
    return render(request, 'ledger/submit_transaction.html', {'transaction_form': transaction_form, 'formset': formset})