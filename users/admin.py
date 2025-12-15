from django.contrib import admin
from users.models import LaboProfile, MedecinProfile, PatientProfile, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "userMail",
        "userName",
        "userForName",
        "userPhone",
        "userDateOfBirth",
        "userAddress",
        "userRole",
        "userGender",
        "is_active",
    )

    list_filter = ("userRole", "userGender")
    search_fields = ("userMail", "userName", "userForName")
    ordering = ("-created_at",)


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user__userName",
        "user__userForName",
        "user__userMail",
        "user__userGender",
        "userGenotype",
        "userBloodGroup",
        "userDiseases",
        "userAllergies",
        "user__is_active",
    )
    search_fields = ("user__userName", "user__userMail")
    list_filter = (
        "userBloodGroup",
        "userGenotype",
        "user__created_at",
        "user__is_active",
    )


@admin.register(MedecinProfile)
class MedecinProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user__userName",
        "user__userForName",
        "user__userMail",
        "user__userGender",
        "user__userPhone",
        "user__userDateOfBirth",
        "user__userAddress",
        "user__is_active",
    )
    search_fields = ("user__userName", "user__userMail")
    list_filter = ("user__created_at", "user__is_active")


@admin.register(LaboProfile)
class LaboProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user__userName",
        "user__userForName",
        "user__userMail",
        "user__userGender",
        "user__userPhone",
        "user__userDateOfBirth",
        "user__userAddress",
        "user__is_active",
    )
    search_fields = ("user__userName", "user__userMail")
    list_filter = ("user__created_at", "user__is_active")
