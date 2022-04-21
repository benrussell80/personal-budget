from django.urls import path, include
from . import views

app_name = 'ledger'
company_relative_urlpatterns = [
    path('', views.company_index, name='company_index'),
    path('qt/create/', views.create_quick_transaction, name='create_quick_transaction'),
    path('qt/submit/', views.submit_quick_transaction, name='submit_quick_transaction'),
    path('account/create/', views.create_account, name='create_account'),
    path('account/<int:pk>/activity/', views.account_overview, name='account_overview'),
    path('transaction/<int:pk>/detail/', views.transaction_detail, name='transaction_detail'),
    path('rec_trans/from/<int:pk>/', views.create_rec_trans, name='create_rec_trans'),
    path('rec_trans/list/', views.list_rec_trans, name='list_rec_trans'),
    path('rec_trans/<int:rec_trans_pk>/edit/', views.edit_recurring_transaction, name='edit_recurring_transaction'),
    path('transaction/submit/', views.submit_transaction, name='submit_transaction'),
    path('transaction/<int:transaction_pk>/edit/', views.edit_transaction, name='edit_transaction'),
]

urlpatterns = [
    path('', views.index, name='index'),
    path('company/<int:company_pk>/', include(company_relative_urlpatterns)),
    path('tax_calculator/', views.tax_calculator, name='tax_calculator'),
    path('company/create/', views.create_company, name='create_company'),
]