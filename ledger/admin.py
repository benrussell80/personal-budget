from django.contrib import admin
from . import models

# Register your models here.
class DetailInline(admin.TabularInline):
    model = models.Detail


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    inlines = [DetailInline]


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'is_leaf']


admin.site.register(models.Detail)
admin.site.register(models.UserDefinedAttribute)
admin.site.register(models.UserDefinedAttributeDetailThrough)
admin.site.register(models.QuickTransaction)
admin.site.register(models.RecurringTransaction)
admin.site.register(models.Company)
