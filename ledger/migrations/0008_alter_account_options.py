# Generated by Django 4.0.1 on 2022-01-26 00:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0007_account_opening_date'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='account',
            options={'ordering': ['key']},
        ),
    ]
