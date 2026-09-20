from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "product_type", "category", "sale_price", "is_active")
    list_filter = ("is_active", "product_type", "category")
    search_fields = ("name",)
