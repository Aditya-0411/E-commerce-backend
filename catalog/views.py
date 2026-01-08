import secrets, string, uuid
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from rest_framework import status, permissions, viewsets, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from .permissions import IsSellerApproved  # ♻️ REFACTORED: Import custom permission
from .models import (
    Category, Product, ProductImage, Cart, CartItem, Order, OrderItem,
    Review, Voucher, PaymentTransaction, Address
)
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductSerializer, ProductCreateSerializer, ProductImageSerializer,
    ReviewSerializer, CartSerializer, AddToCartSerializer,
    OrderSerializer, OrderCreateSerializer, SellerProductSerializer,  # ✨ ADDED OrderCreateSerializer
    VoucherSerializer, VoucherPurchaseSerializer, PaymentTransactionSerializer,
    PaymentInitiateSerializer, AddressSerializer  # ✨ ADDED AddressSerializer
)

import secrets
import string
import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Import necessary models and serializers
from .models import Order, Voucher, PaymentTransaction
from .serializers import (
    OrderSerializer, VoucherSerializer, VoucherPurchaseSerializer,
    PaymentTransactionSerializer, PaymentInitiateSerializer
)

class StandardPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"


# --- Category & Product Views (No changes) ---
class CategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related("category", "seller").prefetch_related(
            "images")
        category_slug = self.request.query_params.get("category__slug")
        search = self.request.query_params.get("search")
        ordering = self.request.query_params.get("ordering", "-created_at")

        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        if search:
            queryset = queryset.filter(title__icontains=search)

        return queryset.order_by(ordering)


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    queryset = Product.objects.filter(is_active=True).prefetch_related("images")
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'


# --- Review View (No changes) ---
class ProductReviewView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Review.objects.filter(product__slug=self.kwargs['slug']).select_related("user")

    def perform_create(self, serializer):
        product = get_object_or_404(Product, slug=self.kwargs['slug'], is_active=True)
        serializer.save(user=self.request.user, product=product)


# --- Cart Views ---
# ... (No major changes to CartView, CartUpdateItemView, CartClearView)
class CartView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def get_object(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart


class CartAddView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data["product"]
        qty = serializer.validated_data["qty"]
        is_preorder = serializer.validated_data["is_preorder"]
        deposit_amount = serializer.validated_data["deposit_amount"]

        cart, _ = Cart.objects.get_or_create(user=request.user)
        deposit_snap = deposit_amount if is_preorder else (product.price + product.gst_amount)

        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={"qty": qty, "price_snapshot": product.price,"preorder_deposit_snapshot": deposit_snap}
        )
        if not created:
            item.qty += qty
            item.save()

        cart_serializer = CartSerializer(cart, context={"request": request})
        return Response(cart_serializer.data, status=status.HTTP_200_OK)


class CartUpdateItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        item_id = request.data.get("item_id")
        qty = int(request.data.get("qty", 1))
        item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)

        if qty <= 0:
            item.delete()
        else:
            if item.product.stock < qty:
                return Response({"detail": f"Insufficient stock for {item.product.title}."}, status=400)
            item.qty = qty
            item.save()

        cart = Cart.objects.get(user=request.user)
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartClearView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response({"detail": "Cart cleared."}, status=status.HTTP_204_NO_CONTENT)


# ✨ ADDED: ViewSet for users to manage their addresses.
class AddressViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# --- Order Views ---
class OrderListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items", "shipping_address").order_by(
            '-created_at')


# ♻️ REFACTORED: Order creation now uses a dedicated serializer for address and voucher.
class OrderCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderCreateSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        cart = get_object_or_404(Cart, user=request.user)
        if not cart.items.exists():
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Check stock for all items before proceeding
        for item in cart.items.select_related("product"):
            if item.product.stock < item.qty:
                return Response({"detail": f"Insufficient stock for {item.product.title}."}, status=400)

        order = Order.objects.create(
            user=request.user,
            shipping_address=validated_data['address_id'],
            voucher=validated_data.get('voucher_code')
        )

        order_items = []
        for item in cart.items.all():
            product = item.product
        if getattr(product, "is_prebook_enabled", False):
            price_to_charge = product.prebook_amount
            is_prebook = True
        else:
            price_to_charge = item.price_snapshot
            is_prebook = False
            product.stock -= item.qty
            product.save(update_fields=["stock"])
            order_items.append(OrderItem(
                order=order, product=product,
                title_snapshot=product.title, price_snapshot=item.price_snapshot, qty=item.qty,is_prebook=is_prebook
            ))
        OrderItem.objects.bulk_create(order_items)

        order.calculate_totals()  # This now handles discounts
        cart.items.all().delete()

        output_serializer = OrderSerializer(order, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


# --- Seller Management Views ---
class SellerProductViewSet(viewsets.ModelViewSet):
    # ♻️ REFACTORED: Using the correct permission class from permissions.py
    permission_classes = [IsSellerApproved]

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user).prefetch_related('images', 'category')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateSerializer
        return SellerProductSerializer

    def perform_create(self, serializer):
        title = serializer.validated_data['title']
        slug = f"{slugify(title)}-{get_random_string(6)}"
        sku = f"SKU-{get_random_string(8).upper()}"
        serializer.save(seller=self.request.user, slug=slug, sku=sku)

    # ♻️ REFACTORED: Simplified create/update methods using DRF defaults, which is cleaner.
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # Return the more detailed SellerProductSerializer
        output_serializer = SellerProductSerializer(serializer.instance, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # Return the more detailed SellerProductSerializer
        output_serializer = SellerProductSerializer(serializer.instance, context={'request': request})
        return Response(output_serializer.data)


class ProductImageUploadView(APIView):
    permission_classes = [IsSellerApproved]

    def post(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        product = get_object_or_404(Product, id=product_id, seller=request.user)

        files = request.FILES.getlist('images')
        if not files:
            return Response({"detail": "No images provided."}, status=status.HTTP_400_BAD_REQUEST)

        images_data = []
        for file in files:
            img = ProductImage.objects.create(product=product, image=file)
            images_data.append(ProductImageSerializer(img, context={'request': request}).data)

        return Response(images_data, status=status.HTTP_201_CREATED)


# ✨ ADDED: View for sellers to list their orders and update status.
class SellerOrderListView(generics.ListAPIView):
    permission_classes = [IsSellerApproved]
    serializer_class = OrderSerializer  # Showing full order details is more useful

    def get_queryset(self):
        # Return orders that contain at least one item from the seller.
        return Order.objects.filter(
            items__product__seller=self.request.user
        ).distinct().prefetch_related('items', 'shipping_address').order_by('-created_at')


class SellerOrderManagementView(generics.UpdateAPIView):
    permission_classes = [IsSellerApproved]
    serializer_class = OrderSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Order.objects.filter(items__product__seller=self.request.user).distinct()

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['shipped', 'delivered', 'cancelled']:
            return Response({'detail': 'Invalid status provided.'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        if new_status == 'shipped':
            from django.utils import timezone
            order.shipped_at = timezone.now()

        order.save(update_fields=['status', 'shipped_at'])
        return Response(self.get_serializer(order).data)

# --- Voucher & Payment Views (No major changes) ---
# ...
# ------------------ Voucher Views ------------------

def generate_voucher_code(length=10):
    """Helper function to generate a unique voucher code."""
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(characters) for _ in range(length))
        if not Voucher.objects.filter(code=code).exists():
            return code


class VoucherPurchaseView(APIView):
    """
    Allows an authenticated user to purchase a new voucher of a specific value.
    POST: /api/vouchers/purchase/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VoucherPurchaseSerializer(data=request.data)
        if serializer.is_valid():
            value = serializer.validated_data['value']
            code = generate_voucher_code()

            voucher = Voucher.objects.create(
                code=code,
                value=value,
                user=request.user
            )
            return Response(VoucherSerializer(voucher).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VoucherListView(generics.ListAPIView):
    """
    Lists all vouchers belonging to the currently authenticated user.
    GET: /api/vouchers/
    """
    serializer_class = VoucherSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Voucher.objects.filter(user=self.request.user).order_by('-created_at')


# ------------------ Payment Gateway Views ------------------

class PaymentInitiateView(APIView):
    """
    Initiates the payment process for a specific order.
    POST: /api/payment/initiate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentInitiateSerializer(data=request.data)
        if serializer.is_valid():
            order_id = serializer.validated_data['order_id']
            gateway = serializer.validated_data['payment_gateway']

            order = get_object_or_404(Order, id=order_id, user=request.user)

            if order.payment_status == 'completed':
                return Response({"detail": "This order has already been paid for."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate a unique transaction ID for the payment attempt
            transaction_id = f"{gateway.upper()}_{uuid.uuid4().hex[:12]}"

            # Create a record of this payment attempt in the database
            PaymentTransaction.objects.create(
                order=order,
                transaction_id=transaction_id,
                payment_gateway=gateway,
                amount=order.total,
                status='initiated'
            )

            # Update the order to reflect the pending payment
            order.payment_status = 'processing'
            order.payment_method = gateway
            order.payment_transaction_id = transaction_id
            order.save(update_fields=['payment_status', 'payment_method', 'payment_transaction_id'])

            # This is where you would integrate with a real payment gateway SDK.
            # The response data prepares the frontend with the necessary info.
            response_data = {
                'transaction_id': transaction_id,
                'order_id': order.id,
                'amount': float(order.total),
                'currency': 'INR',
                'gateway': gateway,
                'gateway_data': self._prepare_gateway_data(order, transaction_id, gateway)
            }

            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _prepare_gateway_data(self, order, transaction_id, gateway):
        """
        Prepares a placeholder dictionary for gateway-specific data.
        In a real application, you'd use the gateway's library to generate this.
        """
        customer_details = {
            'name': order.user.name,
            'email': order.user.email,
            'phone': order.user.phone_number
        }
        # This is example data. You must replace keys and URLs with your actual credentials.
        if gateway == 'razorpay':
            return {
                'key': 'YOUR_RAZORPAY_KEY_ID',
                'order_id': transaction_id, # Razorpay's order_id can be your transaction_id
                'callback_url': '/api/payment/callback/razorpay/',
                'prefill': customer_details
            }
        return {}


class PaymentCallbackView(APIView):
    """
    Handles the incoming webhook/callback from the payment gateway after a payment attempt.
    This view should not have authentication, as the request comes from the gateway server.
    POST: /api/payment/callback/<gateway>/
    """
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, gateway):
        # Extract the transaction ID from the gateway's response data
        transaction_id = request.data.get('transaction_id') or request.data.get('txnid')
        if not transaction_id:
            return Response({"detail": "Transaction ID is missing in callback data."}, status=status.HTTP_400_BAD_REQUEST)

        payment_transaction = get_object_or_404(PaymentTransaction, transaction_id=transaction_id)
        order = payment_transaction.order

        # Verify the authenticity of the callback (critical for security)
        is_payment_successful = self._process_gateway_response(gateway, request.data, payment_transaction)

        if is_payment_successful:
            payment_transaction.status = 'success'
            order.payment_status = 'completed'
            order.status = 'paid'
        else:
            payment_transaction.status = 'failed'
            order.payment_status = 'failed'

        # Store the full response from the gateway for auditing
        payment_transaction.gateway_response = request.data
        payment_transaction.save()
        order.save(update_fields=['payment_status', 'status'])

        # You can also trigger post-payment actions here, like sending emails.

        return Response({
            'status': 'success' if is_payment_successful else 'failed',
            'order_id': order.id,
        })

    def _process_gateway_response(self, gateway, data, payment_transaction):
        """
        Processes the gateway-specific response.
        **CRITICAL:** This is where you must verify the payment signature or hash
        to ensure the callback is legitimate and not forged.
        """
        if gateway == 'razorpay':
            # Example: A real implementation would use the razorpay-python library
            # to verify the signature received in the callback.
            # a = client.utility.verify_payment_signature({...})
            return data.get('status') == 'success' # Placeholder logic

        return False


class PaymentStatusView(APIView):
    """
    Allows a user to check the payment status of their own order.
    GET: /api/payment/status/<order_id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        transactions = order.payment_transactions.all().order_by('-created_at')

        return Response({
            'order_id': order.id,
            'payment_status': order.payment_status,
            'order_status': order.status,
            'total_amount': order.total,
            'transactions': PaymentTransactionSerializer(transactions, many=True).data
        })
