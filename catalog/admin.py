# store/admin.py

from django.contrib import admin
from .models import (
    Category, Product, ProductImage, Review, Cart, Order, OrderItem,
    PlatformSettings, PaymentTransaction, Address, Voucher
)
from django.utils.html import format_html
# ✅ FIXED: Removed all duplicate class definitions.

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'category', 'price', 'stock', 'is_active', 'created_at','preorder_deposit',
        'is_preorder',)
    list_filter = ('is_active', 'category', 'created_at')
    list_editable = ("price", "stock",'is_preorder', 'preorder_deposit')
    search_fields = ('title', 'brand', 'sku')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductImageInline]
    raw_id_fields = ('seller',) # ✨ ADDED: Improves performance for user selection

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'gst_rate', 'icon_preview')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('gst_rate',)
    fields = ('name', 'slug', 'gst_rate', 'icon','icon_preview')
    readonly_fields = ('icon_preview',)

    def icon_preview(self, obj):
        if obj.icon:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit:contain; border-radius:6px;" />',
                obj.icon.url
            )
        return "-"
    icon_preview.short_description = "Icon Preview"

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'title_snapshot', 'price_snapshot', 'qty', 'subtotal', 'gst_amount')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'payment_status', 'total', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    readonly_fields = ('subtotal', 'gst_amount', 'discount_amount', 'commission', 'total', 'created_at', 'shipped_at')
    inlines = [OrderItemInline]
    raw_id_fields = ('user', 'shipping_address', 'voucher') # ✨ ADDED

@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ('platform_commission_rate', 'updated_at')

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'order', 'payment_gateway', 'amount', 'status', 'created_at')
    list_filter = ('payment_gateway', 'status')
    readonly_fields = ('transaction_id', 'gateway_response', 'created_at')
    raw_id_fields = ('order',)

# ✨ ADDED: Register the new Address model
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'address_line_1', 'city', 'state', 'pincode', 'is_default')
    list_filter = ('state', 'city')
    search_fields = ('user__name', 'pincode')
    raw_id_fields = ('user',)

# Register remaining models
admin.site.register(Review)
admin.site.register(Cart)
admin.site.register(Voucher)
