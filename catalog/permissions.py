from rest_framework.permissions import BasePermission

class IsSellerApproved(BasePermission):
    """
    Allow only authenticated users whose SellerProfile is approved.
    """
    message = "Seller account not approved."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        prof = getattr(user, "seller_profile", None)
        return bool(prof and prof.status == "approved")
