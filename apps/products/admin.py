# Rôle : configure Category, Product et ProductPackaging dans l'administration Django.
# Liens : modèles de apps/products/models.py ; pages servies sous admin/ (stock_control/urls.py).
from django.contrib import admin
from .models import Category, Product, ProductPackaging


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


class ProductPackagingInline(admin.TabularInline):
    model = ProductPackaging
    extra = 1
    fields = ('name', 'quantity_per_unit', 'barcode', 'sale_price', 'is_active')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'barcode', 'sku', 'unit', 'purchase_price', 'sale_price', 'profit_margin', 'is_popular', 'is_active')
    list_filter = ('category', 'unit', 'is_popular', 'is_active', 'created_at')
    search_fields = ('name', 'barcode', 'sku', 'description')
    ordering = ('name',)
    inlines = [ProductPackagingInline]
    readonly_fields = ('profit_margin', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'image')
        }),
        ('Identification', {
            'fields': ('barcode', 'sku')
        }),
        ('Pricing', {
            'fields': ('unit', 'purchase_price', 'sale_price', 'tax_rate', 'profit_margin')
        }),
        ('Stock Management', {
            'fields': ('min_stock_threshold', 'is_popular')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(ProductPackaging)
class ProductPackagingAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'quantity_per_unit', 'barcode', 'sale_price', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('product__name', 'name', 'barcode')
    ordering = ('product__name', 'name')
