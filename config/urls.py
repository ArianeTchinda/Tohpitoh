# config/urls.py

from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from users.views import (
    UserViewSet,
    AdminUserViewSet,
    PatientRegisterViewSet,
    MedecinRegisterViewSet,
    LaboRegisterViewSet,
    DEPPatientViewSet,
    AccessControlViewSet,
    DoctorClinicalViewSet,
    LabTestViewSet,
    AdminControlViewSet,
)


router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("admin/users", AdminUserViewSet, basename="admin-user")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    
    # AUTH-1: Connexion
    path("api/login/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    # AUTH-2, AUTH-3: Inscription
    path(
        "api/users/register/patient/",
        PatientRegisterViewSet.as_view({"post": "create"}),
        name="register-patient",
    ),
    path(
        "api/users/register/medecin/",
        MedecinRegisterViewSet.as_view({"post": "create"}),
        name="register-medecin",
    ),
    path(
        "api/users/register/labo/",
        LaboRegisterViewSet.as_view({"post": "create"}),
        name="register-labo",
    ),
    
    # PATIENT (PAT-1, PAT-2, PAT-3)
    path('api/dep/patient/consult/', DEPPatientViewSet.as_view({'get': 'consult_dep'}), name='patient-consult-dep'),
    path('api/dep/patient/prescriptions/', DEPPatientViewSet.as_view({'get': 'list_prescriptions'}), name='patient-list-prescriptions'),
    path('api/dep/patient/lab-results/', DEPPatientViewSet.as_view({'get': 'list_lab_results'}), name='patient-list-lab-results'),

    # GESTION DES ACCÈS (PAT-4, PAT-5, DOC-3)
    path('api/dep/access/grant/', AccessControlViewSet.as_view({'post': 'grant_access'}), name='access-grant'),
    path('api/dep/access/<int:pk>/revoke/', AccessControlViewSet.as_view({'post': 'revoke_access'}), name='access-revoke'),
    path('api/dep/access/check/', AccessControlViewSet.as_view({'get': 'check_access_and_consult'}), name='access-check-consult'),

    # MÉDECIN (DOC-4, DOC-5, DOC-6)
    path('api/dep/doctor/add-note/', DoctorClinicalViewSet.as_view({'post': 'add_note'}), name='doctor-add-note'),
    path('api/dep/doctor/create-prescription/', DoctorClinicalViewSet.as_view({'post': 'create_prescription'}), name='doctor-create-prescription'),
    path('api/dep/doctor/interpret-lab-result/<int:pk>/', DoctorClinicalViewSet.as_view({'patch': 'interpret_lab_result'}), name='doctor-interpret-lab'),
    
    # LABORATOIRE (LAB-1, LAB-2, LAB-3)
    path('api/dep/labo/examens/', LabTestViewSet.as_view({'get': 'list'}), name='labo-list-tests'),
    path('api/dep/labo/examens/<int:pk>/set-status/', LabTestViewSet.as_view({'patch': 'set_status'}), name='labo-set-status'),
    path('api/dep/labo/examens/<int:pk>/upload-result/', LabTestViewSet.as_view({'post': 'upload_result'}), name='labo-upload-result'),

    # --- ROUTES ADMIN ---
    
    # ADMINISTRATION (ADM-1, ADM-5)
    path('api/admin/pending-pros/', AdminControlViewSet.as_view({'get': 'list_pending_professionals'}), name='admin-pending-pros'),
    path('api/admin/pros/<int:pk>/validate/', AdminControlViewSet.as_view({'patch': 'validate_professional'}), name='admin-validate-pro'),
    path('api/admin/logs/', AdminControlViewSet.as_view({'get': 'audit_logs'}), name='admin-audit-logs'),
    
    # DRF SPECTACULAR
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
    # Base Router pour /users et /admin/users
    path("api/", include(router.urls)),
]