# Generated by Django 4.0.3 on 2022-04-13 00:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0012_alter_company_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='company',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to='ledger.company'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='quicktransaction',
            name='company',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='quick_transactions', to='ledger.company'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transaction',
            name='company',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='ledger.company'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='userdefinedattribute',
            name='company',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='udf_attributes', to='ledger.company'),
            preserve_default=False,
        ),
    ]
