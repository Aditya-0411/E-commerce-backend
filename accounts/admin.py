from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from django.forms import ModelForm

class UserChangeForm(ModelForm):
    class Meta:
        model = User
        fields = "__all__"

class UserAdmin(BaseUserAdmin):
    model = User
    form = UserChangeForm
    list_display = ("name", "phone_number", "email", "is_staff", "is_superuser")
    list_filter = ("is_staff", "is_superuser", "gender")
    search_fields = ("phone_number", "name", "email")
    ordering = ("phone_number",)
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("name", "email", "gender", "date_of_birth", "referral_code")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "password1", "password2", "name", "email"),
        }),
    )

admin.site.register(User, UserAdmin)

from django.contrib import admin
from .models import SellerProfile

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'shop_name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__name', 'shop_name', 'pan_no', 'gst_no')
