# store/models.py

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from decimal import Decimal

# Reference the custom user model from your accounts app
User = settings.AUTH_USER_MODEL

# ✨ ADDED: A tuple of official Indian GST slabs for accurate tax calculation.
GST_SLABS = (
    (Decimal('0.00'), '0%'),
    (Decimal('5.00'), '5%'),
    (Decimal('12.00'), '12%'),
    (Decimal('18.00'), '18%'),
    (Decimal('28.00'), '28%'),
)


class PlatformSettings(models.Model):
    platform_commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('5.00'),  # <<< FIX 1: CHANGE 5.00 (float) to Decimal('5.00')
        help_text="Platform commission percentage (e.g., 5.0 for 5%)"
    )
    # ✨ ADDED: Fields for updated_at to track changes.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super(PlatformSettings, self).save(*args, **kwargs)

    def __str__(self):
        return "Platform Settings"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    gst_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        choices=GST_SLABS, default=Decimal('18.00'),
        help_text="GST rate in percentage based on official slabs."
    )
    icon = models.ImageField(
        upload_to='category_icons/', blank=True, null=True,
        help_text="Optional category image or icon for UI display."
    )

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    # ... (no changes to the Product model fields)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, help_text="Maximum Retail Price")
    # ✨ ADDED: Pre-booking fields
    is_preorder = models.BooleanField(
        default=False, 
        help_text="Allow purchase even if stock is 0 and requires a deposit."
    )
    preorder_deposit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="The minimum amount the customer must pay to secure the pre-order."
    )
    available_on = models.DateField(
        null=True, 
        blank=True, 
        help_text="Estimated date product will be shipped."
    )

    stock = models.PositiveIntegerField(default=0)
    brand = models.CharField(max_length=100, blank=True, null=True)
    sku = models.CharField(max_length=50, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def gst_amount(self):
        if self.price is None or self.category is None:
            return Decimal('0.00')

        if self.category.gst_rate is not None:
            return (self.price * self.category.gst_rate) / Decimal('100')
        return Decimal('0.00')

    @property
    def price_with_gst(self):
        return self.price + self.gst_amount

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    # ... (no changes here)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt = models.CharField(max_length=150, blank=True, help_text="Alternative text for the image")

    def __str__(self):
        return f"Image for {self.product.title}"


class Review(models.Model):
    # ... (no changes here)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')


class Cart(models.Model):
    # ... (no changes here)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    # ... (no changes here)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=1)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    preorder_deposit_snapshot = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )

    @property
    def subtotal(self):
        # The logic should be directly under the @property decorator.
        if self.price_snapshot is None:
            return Decimal('0.00')
        return self.qty * self.price_snapshot

    @property
    def gst_amount(self):
        if self.subtotal is None or self.product.category is None:
            return Decimal('0.00')

        if self.product.category.gst_rate is not None:
            gst_rate = self.product.category.gst_rate
            # subtotal is Decimal('0.00') if qty/price are None (from previous fix)
            return (self.subtotal * gst_rate) / Decimal('100')
        return Decimal('0.00')

    @property
    def total_with_gst(self):
        return self.subtotal + self.gst_amount


# ✨ ADDED: Address model for managing user shipping addresses.
class Address(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ('home', 'Home'),
        ('office', 'Office'),
        ('other', 'Other'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='home')
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.name} - {self.address_line_1}, {self.city}"

    class Meta:
        verbose_name_plural = "Addresses"


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')

    # ✨ ADDED: Link to the shipping address and voucher used for the order.
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='orders')
    voucher = models.ForeignKey('Voucher', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # ✨ ADDED: Fields for two-stage payment tracking
    is_preorder_order = models.BooleanField(default=False)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    remaining_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # ✨ ADDED: Field to store the discount amount from a voucher.
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(blank=True, null=True)

    # ♻️ REFACTORED: The calculate_totals method now includes deposit logic.
    def calculate_totals(self):
        # Ensure sum starts with Decimal('0.00') for safety
        order_subtotal = sum((item.subtotal for item in self.items.all()), Decimal('0.00'))
        order_gst = sum((item.gst_amount for item in self.items.all()), Decimal('0.00'))
        settings, _ = PlatformSettings.objects.get_or_create(pk=1)

        # 1. Calculate the FULL gross total (for reference/remaining due calculation)
        full_gross_total = order_subtotal + order_gst

        # 2. Determine the immediate payment required (Deposit + Full Price for non-preorder items)
        # Check if ANY item is a pre-order item to flag the entire order
        self.is_preorder_order = any(
            getattr(item.product, 'is_preorder', False)
            for item in self.items.all()
        )
        # Calculate the sum of required deposit amounts (or full price for standard items)
        deposit_sum_required = Decimal('0.00')
        for item in self.items.all():
            is_preorder = getattr(item.product, 'is_preorder', False)
            if is_preorder:
                # Use the deposit snapshot * quantity
                # Safely access 'preorder_deposit_snapshot' which must be added to CartItem model
                deposit_snap = getattr(item, 'preorder_deposit_snapshot', item.price_snapshot) 
                deposit_sum_required += (deposit_snap * item.qty)
            else:
                # Use the item's full gross price for standard items
                deposit_sum_required += (item.subtotal + item.gst_amount)

        # 3. Apply Voucher Discount
        discount = Decimal('0.00')
        if self.voucher and not self.voucher.is_used:
            discount = self.voucher.value
            self.voucher.is_used = True
            self.voucher.save()
        self.discount_amount = discount

        # 4. Finalize Totals
        self.subtotal = order_subtotal
        self.gst_amount = order_gst
        self.commission = (order_subtotal * settings.platform_commission_rate) / Decimal('100')

        # The actual amount due NOW after discount
        self.deposit_amount = deposit_sum_required - self.discount_amount
        # The remaining amount (Total Full Price - Deposit Paid)
        self.remaining_due = full_gross_total - self.deposit_amount
        # CRITICAL: self.total holds the amount the customer pays NOW at checkout.
        self.total = self.deposit_amount

        # Ensure remaining_due is not negative (in case discount exceeded the deposit)
        if self.remaining_due < Decimal('0.00'):
            self.remaining_due = Decimal('0.00')
        # 💥 CRITICAL FIX: The save method must be called to persist changes 💥
        self.save()

    def __str__(self):
        return f"Order #{self.id} by {self.user.email}"


class OrderItem(models.Model):
    # ... (no changes here)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    title_snapshot = models.CharField(max_length=200)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    qty = models.PositiveIntegerField(default=1)
    is_prebook = models.BooleanField(default=False)

    @property
    def subtotal(self):
        # FIX: Check if price_snapshot is None before multiplying.
        if self.price_snapshot is None:
            from decimal import Decimal
            return Decimal('0.00')
        return self.qty * self.price_snapshot

    @property
    def gst_amount(self):
        if self.product.category and self.product.category.gst_rate is not None:
            gst_rate = self.product.category.gst_rate
            return (self.subtotal * gst_rate) / Decimal('100')
        return Decimal('0.00')


class Voucher(models.Model):
    # ... (no changes here)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vouchers')
    code = models.CharField(max_length=15, unique=True)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class PaymentTransaction(models.Model):
    # ... (no changes here)
    GATEWAY_CHOICES = (
        ('razorpay', 'Razorpay'),
        ('payu', 'PayU'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
    )
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_transactions')
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    gateway_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
