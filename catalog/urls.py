# catalog/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryListView, ProductListView, ProductDetailView, ProductReviewView,
    CartView, CartAddView, CartUpdateItemView, CartClearView,
    OrderListView, OrderCreateView,
    SellerProductViewSet, ProductImageUploadView,
    VoucherPurchaseView, VoucherListView,
    PaymentInitiateView, PaymentCallbackView, PaymentStatusView,
    AddressViewSet, SellerOrderListView, SellerOrderManagementView  # ✨ ADDED new views
)

router = DefaultRouter()
router.register('seller/products', SellerProductViewSet, basename='seller-products')
router.register('addresses', AddressViewSet, basename='addresses')  # ✨ ADDED address routes

urlpatterns = [
    # Public Catalog
    path("categories/", CategoryListView.as_view(), name="categories"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("products/<slug:slug>/reviews/", ProductReviewView.as_view(), name="product-reviews"),

    # Cart
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/add/", CartAddView.as_view(), name="cart-add"),
    path("cart/update-item/", CartUpdateItemView.as_view(), name="cart-update-item"),
    path("cart/clear/", CartClearView.as_view(), name="cart-clear"),

    # Orders (for customers)
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/create/", OrderCreateView.as_view(), name="order-create"),

    # Vouchers
    path('vouchers/purchase/', VoucherPurchaseView.as_view(), name='voucher-purchase'),
    path('vouchers/', VoucherListView.as_view(), name='voucher-list'),

    # Payment Gateway
    path('payment/initiate/', PaymentInitiateView.as_view(), name='payment-initiate'),
    path('payment/callback/<str:gateway>/', PaymentCallbackView.as_view(), name='payment-callback'),
    path('payment/status/<int:order_id>/', PaymentStatusView.as_view(), name='payment-status'),

    # Seller Management
    path("seller/upload-image/", ProductImageUploadView.as_view(), name="seller-upload-image"),
    # ✨ ADDED new seller order management endpoints
    path("seller/orders/", SellerOrderListView.as_view(), name="seller-orders-list"),
    path("seller/orders/<int:id>/manage/", SellerOrderManagementView.as_view(), name="seller-order-manage"),

    # Include router URLs (for seller products and user addresses)
    path("", include(router.urls)),
]
