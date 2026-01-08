from rest_framework import generics, status, permissions
from rest_framework.decorators import permission_classes, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Notification, SellerProfile
from .serializers import (
    RegisterSerializer, LoginSerializer, NotificationSerializer,
    SellerProfileSerializer, ProfileSerializer
)
import random # for generating OTP
from datetime import timedelta, timezone
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import OTPRequestSerializer, OTPVerifySerializer # <-- You will define these
from django.utils import timezone

def generate_and_send_otp(user):
    otp_code = str(random.randint(100000, 999999))
    user.otp = otp_code
    user.otp_created_at = timezone.now()
    user.save()

    # Placeholder: In production, send this code via SMS to user.phone_number
    print(f"DEBUG: Sending OTP {otp_code} to {user.phone_number}")
    return True  # Return status of sending


class OTPRequestView(APIView):
    """Initiates the login by requesting an OTP."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']

        try:
            user = User.objects.get(phone_number=phone_number)
            generate_and_send_otp(user)
            return Response({"detail": "OTP sent successfully."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)


class OTPVerifyView(APIView):
    """Verifies the OTP and returns JWT tokens."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        otp_code = serializer.validated_data['otp']

        user = serializer.validated_data['user']

        # Successful Verification - Generate Tokens
        refresh = RefreshToken.for_user(user)
        user.otp = None  # Clear OTP after use
        user.save()

        return Response({
            "message": "Login successful",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAdminUser])  # Only admin can approve
def approve_seller(request, seller_id):
    try:
        seller = SellerProfile.objects.get(id=seller_id)
        seller.status = "approved"
        seller.save()
        return Response({"detail": "Seller approved successfully."})
    except SellerProfile.DoesNotExist:
        return Response({"detail": "Seller not found."}, status=404)


class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successful",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)


# ❌ REMOVED: The first, redundant ProfileView was here.

class HomeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "sections": [
                "Notifications",
                "Home Navigation Bar",
                "Profile Page",
                "About Section",
                "Seller Registration"
            ],
            "feature_flags": {
                "wallet": False,   # disabled for now
                "booking": False   # disabled for now
            }
        })

# ✅ KEPT: This is the correct, more functional view for handling user profiles.
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class SellerRegistrationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, "seller_profile", None)
        if not profile:
            return Response({"exists": False, "status": None})
        data = SellerProfileSerializer(profile).data
        data.update({"exists": True})
        return Response(data)

    def post(self, request):
        serializer = SellerProfileSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(SellerProfileSerializer(profile).data, status=201)

class NotificationsListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            n = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        n.is_read = True
        n.save()
        return Response({"ok": True})



class AboutAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # ---------------------------------------------------------------------
        # --- DEFINITION 1: TERMS OF USE ---
        # ---------------------------------------------------------------------
        TERMS_OF_USE_FULL = """
# Zirvanaa Terms and Conditions
This document is an electronic record in terms of Information Technology Act, 2000 and rules
there under as applicable and the amended provisions pertaining to electronic records in various
statutes as amended by the Information Technology Act, 2000. This electronic record is generated
by a computer system and does not require any physical or digital signatures.
This document is published in accordance with the provisions of Rule 3 (1) of the Information
Technology (Intermediaries guidelines) Rules, 2011 that require publishing the rules and
regulations, privacy policy and Terms of Use for access or usage of domain name https://zirvanaa.
com/ ('Website'), including the related mobile site and mobile application (hereinafter referred to
as 'Platform').
The Platform is owned by ZIRVANA ONLINE STORE PRIVATE LIMITED, a company
incorporated under the Companies Act, 1956 with its registered office at ZIRVANA ONLINE
STORE PRIVATE LIMITED, MANDER, RANCHI, 835214, Jharkhand (hereinafter referred
to as ‘Platform Owner’, 'we', 'us', 'our')..
Your use of the Platform and services and tools are governed by the following terms and
conditions (“Terms of Use”) as applicable to the Platform including the applicable policies which
are incorporated herein by way of reference. If You transact on the Platform, You shall be subject
to the policies that are applicable to the Platform for such transaction. By mere use of the Platform,
You shall be contracting with the Platform Owner and these terms and conditions including the
policies constitute Your binding obligations, with Platform Owner. These Terms of Use relate to
your use of our website, goods (as applicable) or services (as applicable) (collectively, 'Services').
Any terms and conditions proposed by You which are in addition to or which conflict with these
Terms of Use are expressly rejected by the Platform Owner and shall be of no force or effect.
These Terms of Use can be modified at any time without assigning any reason. It is your
responsibility to periodically review these Terms of Use to stay informed of updates..
For the purpose of these Terms of Use, wherever the context so requires ‘you’, 'your' or ‘user’ shall
mean any natural or legal person who has agreed to become a user/buyer on the Platform..
ACCESSING, BROWSING OR OTHERWISE USING THE PLATFORM INDICATES YOUR
AGREEMENT TO ALL THE TERMS AND CONDITIONS UNDER THESE TERMS OF USE,
SO PLEASE READ THE TERMS OF USE CAREFULLY BEFORE PROCEEDING..
The use of Platform and/or availing of our Services is subject to the following Terms of Use:
1. To access and use the Services, you agree to provide true, accurate and complete information
to us during and after registration, and you shall be responsible for all acts done through the
use of your registered account on the Platform..
2. Neither we nor any third parties provide any warranty or guarantee as to the accuracy,
timeliness, performance, completeness or suitability of the information and materials offered
on this website or through the Services, for any specific purpose.
9. You understand that upon initiating a transaction for availing the Services you are entering
into a legally binding and enforceable contract with the Platform Owner for the Services..
10. You shall indemnify and hold harmless Platform Owner, its affiliates, group companies (as
applicable) and their respective officers, directors, agents, and employees, from any claim or
demand, or actions including reasonable attorney's fees, made by any third party or penalty
imposed due to or arising out of Your breach of this Terms of Use, privacy Policy and other
Policies, or Your violation of any law, rules or regulations or the rights (including
infringement of intellectual property rights) of a third party.
11. Notwithstanding anything contained in these Terms of Use, the parties shall not be liable for
any failure to perform an obligation under these Terms if performance is prevented or
delayed by a force majeure event..
12. These Terms and any dispute or claim relating to it, or its enforceability, shall be governed
by and construed in accordance with the laws of India..
13. All disputes arising out of or in connection with these Terms shall be subject to the exclusive
jurisdiction of the courts in Ranchi and Jharkhand.
14. All concerns or communications relating to these Terms must be communicated to us using
the contact information provided on this website
"""

        # ---------------------------------------------------------------------
        # --- DEFINITION 2: PRIVACY, REFUND, AND SHIPPING POLICY ---
        # (Combined content for the second tab)
        # ---------------------------------------------------------------------
        PRIVACY_POLICY_FULL = """
# 🔒 Zirvanaa Privacy Policy (DPDP Act, 2023 Compliant)

# --- 1. Introduction & Legal Framework ---
This Privacy Policy describes how ZIRVANA ONLINE STORE PRIVATE LIMITED and its
affiliates (collectively "ZIRVANA ONLINE STORE PRIVATE LIMITED, we, our, us") collect, use,
share, protect or otherwise process your information/ personal data through our website https://zirvanaa.
com/ (hereinafter referred to as Platform). We do not offer any product/service under this Platform outside
India and your personal data will primarily be stored and processed in India. By visiting this Platform,
providing your information or availing any product/service offered on the Platform, you expressly agree
to be bound by the terms and conditions of this Privacy Policy, the Terms of Use and the applicable
service/product terms and conditions, and agree to be governed by the laws of India.

# --- 2. Collection of Data ---
We collect your personal data when you use our Platform, services or otherwise interact with
us during the course of our relationship. Some of the information that we may collect includes but is not limited to personal data / information provided to us
during sign-up/registering or using our Platform such as name, date of birth, address, telephone/mobile
number, email ID and/or any such information shared as proof of identity or address. Sensitive personal data may be collected with your consent, such as your bank account or payment instrument information. We may track your behaviour, preferences, and other information that you choose to provide on our Platform. If you receive an email, a call from a person/association claiming to be ZIRVANA
ONLINE STORE PRIVATE LIMITED seeking any personal data like debit/credit card PIN, netbanking or mobile banking password, we request you to never provide such information.

# --- 3. Usage & Purpose Limitation ---
We use personal data to provide the services you request, assist sellers and business partners in handling and fulfilling orders, enhance customer experience, resolve disputes, inform you about offers and updates, customise your experience, detect and protect us against error, fraud and other criminal activity. You will have the ability to opt-out of marketing uses.

# --- 4. Sharing & Disclosure ---
We may share your personal data internally within our group entities and affiliates. We may disclose personal data to third parties such as sellers, business partners, third party service providers including logistics partners, and payment instrument issuers to provide you access to our services, comply with legal obligations, and enforce user agreement. We may disclose data to government agencies if required by law or in the good faith belief that such disclosure is necessary to respond to subpoenas or protect the rights, property or personal safety of our users or the general public.

# --- 5. Security & Retention ---
To protect your personal data, we adopt reasonable security practices and procedures. Users are responsible for ensuring the protection of login and password records for their account. You have an option to delete your account by visiting your profile and settings on our Platform. We retain your personal data no longer than is required for the purpose for which it was collected or as required under any applicable law.

# --- 6. Your Rights & Consent ---
You may access, rectify, and update your personal data directly through the functionalities provided on the Platform. By visiting our Platform or by providing your information, you consent to the collection, use, storage, disclosure and otherwise processing of your information. You have an option to withdraw your consent by writing to the Grievance Officer, but this withdrawal will not be retrospective.

# --- 7. Refund and Cancellation Policy ---
Cancellations will only be considered if the request is made 7 days of placing the order. Cancellation requests may not be entertained if the orders have been communicated to sellers and they have initiated shipping. In case of receipt of damaged or defective items, please report to our customer service within 7 days of receipt. Refunds for approved requests will take 7 days to process. We offer refund/exchange within first 7 days from the date of purchase, provided the item is unused and in original packaging. Certain categories of products are exempted from returns (e.g., perishables, custom-made).

# --- 8. Shipping Policy ---
Orders are shipped through registered domestic courier companies and/or speed post only. Orders are shipped within 7 days from the date of the order confirmation. Platform Owner shall not be liable for any delay in delivery by the courier company. Delivery will be made to the address provided by the buyer. Shipping costs levied by the seller or Platform Owner are not refundable.
"""

        return Response({
            "app": "Zirvanaa",
            "version": "1.0",
            # --- Location ---
            "headquarters_address": {
                "street": "123 Commercial Hub",
                "city": "Ranchi",
                "state": "Jharkhand",
                "pincode": "834001"
            },
            "about": "Zirvanaa is an e-commerce platform for FMCG, Electronics and Fashion. Our mission is to connect approved sellers with customers across India, providing secure transactions and reliable delivery. Wallet features are coming soon.",
            "contact_email": "Zirvanaastar25pro@gmail.com",
            "contact_number": "+91 9162777530",
            # --- Policy Documents ---
            "policies": {
                "terms_of_use": TERMS_OF_USE_FULL.strip(),
                "privacy_policy": PRIVACY_POLICY_FULL.strip(),
            },

            "feature_flags": {
                "wallet_service": True,
                "loyalty_program": False,
                "international_shipping": False
            }
        })
