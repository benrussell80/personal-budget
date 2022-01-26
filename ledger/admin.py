from django.contrib import admin
from . import models

# Register your models here.
class DetailInline(admin.TabularInline):
    model = models.Detail


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    inlines = [DetailInline]

admin.site.register(models.Account)
admin.site.register(models.Detail)
admin.site.register(models.UserDefinedAttribute)
admin.site.register(models.UserDefinedAttributeDetailThrough)
admin.site.register(models.QuickTransaction)
