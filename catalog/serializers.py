# store/serializers.py

from rest_framework import serializers
from .models import (
    Category, Product, ProductImage, Review, Cart, CartItem, Order, OrderItem,
    Voucher, PaymentTransaction, Address
)

# --- Category & Product Serializers ---

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'gst_rate','icon']
        read_only_fields = ['slug']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt"]
    # ✅ FIXED: The get_image method was redundant as DRF handles this. Removed for simplicity.

class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    thumbnail = serializers.SerializerMethodField()
    # ✅ FIXED: Removed duplicated fields.
    price_with_gst = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    gst_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_preorder = serializers.BooleanField(read_only=True)
    preorder_deposit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    available_on = serializers.DateField(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "title", "slug", "price", "mrp", "price_with_gst", "gst_amount", "brand", "stock", "category", "thumbnail", "is_preorder", "preorder_deposit", "available_on"]

    def get_thumbnail(self, obj):
        img = obj.images.first()
        if img and hasattr(img, 'image') and img.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(img.image.url)
        return None

class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    # ✅ FIXED: Removed duplicated fields.
    price_with_gst = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    gst_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "title", "slug", "description", "price", "mrp", "price_with_gst", "gst_amount", "brand", "sku", "stock", "category", "images", "is_active", "created_at", "is_preorder", "preorder_deposit", "available_on"]

# --- Review Serializer ---

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "user", "user_name", "rating", "comment", "created_at"]
        read_only_fields = ["user"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

# --- Cart Serializers ---

class CartItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    image = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    # ✅ FIXED: Removed duplicated fields.
    gst_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_with_gst = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_is_preorder = serializers.CharField(source='product.is_preorder', read_only=True)
    class Meta:
        model = CartItem
        fields = ["id", "product", "product_title", "qty", "price_snapshot", "subtotal", "gst_amount", "total_with_gst", "image", "product_is_preorder"]

    def get_image(self, obj):
        img = obj.product.images.first()
        if img and hasattr(img, 'image') and img.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(img.image.url)
        return None

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    # ✅ FIXED: Removed duplicated methods.
    total_gst = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()
    # NEW: Calculate prebook totals for the frontend summary
    total_deposit_due = serializers.SerializerMethodField()
    total_full_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total", "total_gst", "grand_total", "updated_at", "total_deposit_due", "total_full_price"]
    def get_total_deposit_due(self, obj):
        # Calculate the sum of required deposits + full price for non-prebook items
        # This mirrors the logic in Order.calculate_totals
        # Since this is complex, we assume the backend correctly calculates and returns the current payment total.
        return sum(
            (item.product.preorder_deposit * item.qty)
            if item.product.is_preorder else (item.subtotal + item.gst_amount)
            for item in obj.items.all()
        )
    def get_total_full_price(self, obj):
        # Calculate the sum of full prices for all items (for context on the checkout page)
        return sum(item.total_with_gst for item in obj.items.all())
    def get_total_gst(self, obj):
        return sum(item.gst_amount for item in obj.items.all())

    def get_grand_total(self, obj):
        return sum(item.total_with_gst for item in obj.items.all())

class AddToCartSerializer(serializers.Serializer):
    # ♻️ REFACTORED: Using PrimaryKeyRelatedField is more robust.
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    qty = serializers.IntegerField(min_value=1)

    def validate(self, data):
        product = data["product"]
        qty = data["qty"]
        
        # Check stock only if it's NOT a pre-order
        if not product.is_preorder and product.stock < qty:
            raise serializers.ValidationError(f"Insufficient stock for {product.title}. Only {product.stock} left.")
            
        # Store whether it's a pre-order in validated_data for the view
        data['is_preorder'] = product.is_preorder
        data['deposit_amount'] = product.preorder_deposit
        return data


# --- Address Serializer ---
# ✨ ADDED: Serializer for the new Address model.
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'address_line_1', 'address_line_2', 'city', 'state', 'pincode', 'address_type', 'is_default']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# --- Order Serializers ---
class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    # ✅ FIXED: Removed duplicated field.
    gst_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "title_snapshot", "price_snapshot", "qty", "subtotal", "gst_amount"]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True) # ✨ ADDED
    voucher_code = serializers.CharField(source='voucher.code', read_only=True, allow_null=True) # ✨ ADDED

    class Meta:
        model = Order
        fields = [
            "id", "status", "payment_status", "subtotal", "gst_amount", "discount_amount", # ✨ ADDED discount_amount
            "total", "shipping_address", "voucher_code", "items", "created_at", "shipped_at"
        ]

# ✨ ADDED: A new serializer to handle order creation with address and voucher.
class OrderCreateSerializer(serializers.Serializer):
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        label="Shipping Address"
    )
    voucher_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_address_id(self, address):
        # Ensure the address belongs to the current user
        user = self.context['request'].user
        if address.user != user:
            raise serializers.ValidationError("This address does not belong to the current user.")
        return address

    def validate_voucher_code(self, code):
        if not code:
            return None
        try:
            voucher = Voucher.objects.get(code=code, is_used=False)
            return voucher
        except Voucher.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired voucher code.")
        return None

# --- Seller Management Serializers ---

class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["title", "description", "price", "mrp", "stock", "is_active", "brand", "category", "is_preorder",       # ✅ correct field name
            "preorder_deposit",  # ✅ correct field name
            "available_on"]
        # ♻️ REFACTORED: SKU should be auto-generated, not user-provided.

class SellerProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "title", "category", "description",
            "price", "stock", "is_prebook_enabled", "prebook_amount",
            "is_active", "created_at"
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        if data.get("is_prebook_enabled") and not data.get("prebook_amount"):
            raise serializers.ValidationError(
                "Prebook amount is required when enabling pre-booking."
            )
        return data

# --- Payment & Voucher Serializers ---

# ✅ FIXED: Removed duplicate PaymentTransactionSerializer and related classes.
class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ['id', 'transaction_id', 'payment_gateway', 'amount', 'currency', 'status', 'created_at']

class PaymentInitiateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    payment_gateway = serializers.ChoiceField(choices=PaymentTransaction.GATEWAY_CHOICES)

class VoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = ['id', 'code', 'value', 'is_used']

class VoucherPurchaseSerializer(serializers.Serializer):
    value = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
