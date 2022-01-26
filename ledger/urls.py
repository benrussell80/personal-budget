from os import name
from django.urls import path
from . import views

app_name = 'ledger'
urlpatterns = [
    path('', views.index, name='index'),
    path('qt/create/', views.create_quick_transaction, name='create_quick_transaction'),
    path('qt/submit/', views.submit_quick_transaction, name='submit_quick_transaction'),
    path('account/create/', views.create_account, name='create_account'),
    path('account/<int:pk>/activity/', views.account_overview, name='account_overview'),
    path('transaction/<int:pk>/detail/', views.transaction_detail, name='transaction_detail'),
    path('transaction/submit/', views.submit_transaction, name='submit_transaction'),
    path('analytics/expenses/', views.expense_analytics, name='expense_analytics'),
    path('analytics/expenses/filter/', views.expense_analytics_filter, name='expense_analytics_filter'),
    path('analytics/', views.analytics, name='analytics'),
]