from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView

from .models import Product, ProductImage
from .serializers import ProductListSerializer,  ProductImageSerializer

class AdminProductViewSet(viewsets.ModelViewSet):
    """
    /api/admin/catalog/products/
    """
    queryset = Product.objects.select_related("category", "seller").prefetch_related("images").all()
    permission_classes = [IsAdminUser]

#def get_serializer_class(self):
       # if self.action in ["list", "retrieve"]:
       #     return ProductListSerializer
      #  return ProductCreateUpdateSerializer

    def create(self, request, *args, **kwargs):
        # Admin chooses the seller (or later you can default to admin)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = Product.objects.create(seller_id=request.data.get("seller"), **serializer.validated_data)
        out = ProductListSerializer(product, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        out = ProductListSerializer(product, context={"request": request})
        return Response(out.data)

class AdminProductImageUploadView(APIView):
    """
    POST /api/admin/catalog/products/<int:pk>/images/
    form-data: image (file), alt (optional)
    """
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        file = request.FILES.get("image")
        if not file:
            return Response({"detail": "No image file."}, status=400)
        img = ProductImage.objects.create(product=product, image=file, alt=request.data.get("alt", ""))
        return Response(ProductImageSerializer(img, context={"request": request}).data, status=201)
