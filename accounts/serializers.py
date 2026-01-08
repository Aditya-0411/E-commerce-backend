from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, SellerProfile, Notification
from datetime import date
from datetime import timedelta
from django.utils import timezone


class OTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)


class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    otp = serializers.CharField(required=True, max_length=6)

    def validate(self, data):
        phone_number = data.get('phone_number')
        otp_code = data.get('otp')

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid phone number or OTP.")

        # Check if the submitted OTP matches and is not expired (e.g., 5 minutes)
        otp_expiry_time = timezone.now() - timedelta(minutes=5)

        if not user.otp or user.otp != otp_code or user.otp_created_at < otp_expiry_time:
            raise serializers.ValidationError("Invalid or expired OTP.")

        if not user.is_active:
            raise serializers.ValidationError("User account disabled.")

        data['user'] = user
        return data
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "name", "phone_number", "email", "gender", "date_of_birth", "referral_code", "password"]

    def validate_date_of_birth(self, value):
        # Extra safety check: validate age server-side (in addition to model validator)
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18:
            raise serializers.ValidationError("User must be at least 18 years old.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone_number = data.get("phone_number")
        password = data.get("password")
        if phone_number and password:
            user = authenticate(username=phone_number, password=password)
            if not user:
                raise serializers.ValidationError("Invalid phone number or password.")
            if not user.is_active:
                raise serializers.ValidationError("User account disabled.")
            data["user"] = user
            return data
        raise serializers.ValidationError("Must include phone_number and password.")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "phone_number", "email", "gender", "date_of_birth", "referral_code", "date_joined"]


class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerProfile
        read_only_fields = ["status", "created_at"]
        fields = [
            "shop_name","pan_no","bank_account_number","bank_name","ifsc","branch","gst_no","status","created_at"
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        # Upsert-like behavior
        profile, created = SellerProfile.objects.update_or_create(
            user=user, defaults=validated_data
        )
        return profile

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "is_read", "created_at"]


class ProfileSerializer(serializers.ModelSerializer):
    is_seller = serializers.SerializerMethodField()
    seller_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["name", "phone_number", "email", "gender", "date_of_birth", "referral_code", "is_seller", "seller_status"] # <--- Add the new fields here

    def get_is_seller(self, obj):
        # The related name on the SellerProfile model is 'seller_profile', not 'sellerprofile'
        return hasattr(obj, "seller_profile")

    def get_seller_status(self, obj):
        # Use the correct related name 'seller_profile'
        return obj.seller_profile.status if hasattr(obj, "seller_profile") else None