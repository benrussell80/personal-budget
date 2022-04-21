# Generated by Django 4.0.3 on 2022-04-21 16:34

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0013_account_company_quicktransaction_company_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='recurringtransaction',
            name='company',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='recurring_transactions', to='ledger.company'),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='RecurringTransactionDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credit', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ('debit', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ('notes', models.TextField(blank=True, null=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='recurring_transaction_details', to='ledger.account')),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='details', to='ledger.recurringtransaction')),
            ],
        ),
    ]
