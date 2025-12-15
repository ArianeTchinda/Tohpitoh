# users/views.py

from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.status import (
    HTTP_201_CREATED, 
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN, 
    HTTP_200_OK, 
    HTTP_404_NOT_FOUND
)
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser # Importation pour l'upload de fichiers

from django.db.models import Q # Importation pour les requêtes complexes
from datetime import timedelta # Importation pour la gestion de l'expiration
from django.utils import timezone # Importation pour la gestion des dates/heures
from django.shortcuts import get_object_or_404 # Importation pour les objets non trouvés

from users.models import (
    ClinicalNote, Prescription, LabTest, AccessAuthorization, User, AuditLog
)
from users.serializers import (
    ClinicalNoteSerializer, PrescriptionSerializer, LabTestSerializer, 
    AccessAuthorizationSerializer, LabTestResultUploadSerializer, LabTestInterpretationSerializer, 
    CreateAccessRequestSerializer, AuditLogSerializer,
    LaboRegisterSerializer,
    MedecinRegisterSerializer,
    PatientRegisterSerializer,
    UserSerializer,
    UserRegisterSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
)
from users.permissions import IsPatient, IsDoctor, IsLabo # Importation des permissions personnalisées

from drf_spectacular.utils import extend_schema


@extend_schema(
    tags=["Utilisateur"],
    description="Opérations CRUD pour l'utilisateur connecté.",
)
class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("-created_at")

    def get_permissions(self):
        if self.action in ["list"]:
            return [IsAdminUser()]
        if self.action in [
            "retrieve",
            "update",
            "partial_update",
            "destroy",
            "change_password",
        ]:
            return [IsAuthenticated()]

        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        if self.action == "change_password":
            return ChangePasswordSerializer

        return UserSerializer

    def get_queryset(self):
        # Un user normal ne voit que lui-même.
        if self.request.user.is_staff or self.request.user.is_superuser:
            return User.objects.all().order_by("-created_at")

        return User.objects.filter(id=self.request.user.id)


@extend_schema(
    tags=["Administration"],
    description="Gestion des utilisateurs réservée aux administrateurs.",
)
class AdminUserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return UserUpdateSerializer

        return UserSerializer


@extend_schema(
    tags=["Inscription"],
    description="Inscription d’un patient avec création automatique du profil patient.",
)
class PatientRegisterViewSet(GenericViewSet):
    serializer_class = PatientRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=HTTP_201_CREATED)


@extend_schema(
    tags=["Inscription"],
    description="Inscription d’un médecin avec création automatique du profil médecin.",
)
class MedecinRegisterViewSet(GenericViewSet):
    serializer_class = MedecinRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=HTTP_201_CREATED)


@extend_schema(
    tags=["Inscription"],
    description="Inscription d’un laboratoire avec création automatique du profil labo.",
)
class LaboRegisterViewSet(GenericViewSet):
    serializer_class = LaboRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=HTTP_201_CREATED)


@extend_schema(tags=["Patient - Mon DEP"])
class DEPPatientViewSet(GenericViewSet):
    """Fonctionnalités du Patient (PAT-1, PAT-2, PAT-3)."""
    permission_classes = [IsPatient]

    # /api/dep/patient/consult
    @action(detail=False, methods=['get'])
    def consult_dep(self, request):
        """PAT-1: Consultation agrégée du DEP."""
        user = request.user
        
        notes = ClinicalNoteSerializer(
            ClinicalNote.objects.filter(patient=user).order_by('-created_at'), many=True
        ).data
        prescriptions = PrescriptionSerializer(
            Prescription.objects.filter(patient=user).order_by('-created_at'), many=True
        ).data
        lab_results = LabTestSerializer(
            LabTest.objects.filter(patient=user, status=LabTest.TestStatus.COMPLETED).order_by('-created_at'), many=True
        ).data
        
        # Vous pouvez ajouter ici l'agrégation des données vitales du PatientProfile
        
        return Response({
            'clinical_notes': notes,
            'prescriptions': prescriptions,
            'lab_results': lab_results,
            # 'patient_profile': PatientProfileSerializer(user.patient_profile.first()).data 
        })
    
    # /api/dep/patient/prescriptions/ (PAT-2)
    @action(detail=False, methods=['get'], url_path='prescriptions')
    def list_prescriptions(self, request):
        """PAT-2: Liste des ordonnances."""
        prescriptions = Prescription.objects.filter(patient=request.user).order_by('-created_at')
        return Response(PrescriptionSerializer(prescriptions, many=True).data)

    # /api/dep/patient/lab-results/ (PAT-3)
    @action(detail=False, methods=['get'], url_path='lab-results')
    def list_lab_results(self, request):
        """PAT-3: Liste des résultats de laboratoire."""
        lab_results = LabTest.objects.filter(patient=request.user).order_by('-created_at')
        return Response(LabTestSerializer(lab_results, many=True).data)


@extend_schema(tags=["Patient/Médecin - Gestion des Accès"])
class AccessControlViewSet(GenericViewSet):
    """PAT-4, PAT-5, DOC-2, DOC-3 : Gestion et vérification des autorisations d'accès."""
    permission_classes = [IsAuthenticated]

    # /api/dep/access/grant/
    @action(detail=False, methods=['post'], permission_classes=[IsPatient])
    def grant_access(self, request):
        """PAT-4: Accorder l'accès à un professionnel."""
        serializer = CreateAccessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        professional_email = serializer.validated_data['professional_email']
        expiration_days = serializer.validated_data['expiration_days']
        
        try:
            # Vérifier l'existence et le rôle du professionnel
            professional = User.objects.get(userMail__iexact=professional_email)
            if professional.userRole not in [User.TypeRole.MEDECIN, User.TypeRole.LABORATOIRE]:
                return Response({"detail": "L'e-mail ne correspond pas à un professionnel de santé valide."}, 
                                status=HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"detail": "Professionnel non trouvé."}, status=HTTP_404_NOT_FOUND)

        # Créer ou mettre à jour l'autorisation
        expires_at = timezone.now() + timedelta(days=expiration_days)
        auth, created = AccessAuthorization.objects.update_or_create(
            patient=request.user, 
            professional=professional,
            defaults={'is_active': True, 'expires_at': expires_at}
        )
        
        return Response(AccessAuthorizationSerializer(auth).data, status=HTTP_201_CREATED)

    # /api/dep/access/{pk}/revoke/
    @action(detail=True, methods=['post'], permission_classes=[IsPatient])
    def revoke_access(self, request, pk=None):
        """PAT-5: Révoquer l'accès à un professionnel (pk est l'ID de l'autorisation)."""
        try:
            auth = AccessAuthorization.objects.get(pk=pk, patient=request.user, is_active=True)
        except AccessAuthorization.DoesNotExist:
            return Response({"detail": "Autorisation non trouvée ou déjà révoquée."}, status=HTTP_404_NOT_FOUND)

        auth.is_active = False
        auth.save()
        return Response({"detail": "Accès révoqué avec succès."}, status=HTTP_200_OK)

    # /api/dep/access/check/?patient_id=X (DOC-3 vérification et consultation)
    @action(detail=False, methods=['get'], permission_classes=[IsDoctor | IsLabo], url_path='check')
    def check_access_and_consult(self, request):
        """DOC-3: Vérifie l'accès et retourne le DEP si autorisé."""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({"detail": "patient_id est requis."}, status=HTTP_400_BAD_REQUEST)

        try:
            patient = User.objects.get(id=patient_id, userRole=User.TypeRole.PATIENT)
        except User.DoesNotExist:
            return Response({"detail": "Patient non trouvé."}, status=HTTP_404_NOT_FOUND)
        
        # Vérification de l'autorisation
        auth = AccessAuthorization.objects.filter(patient=patient, professional=request.user).first()
        
        if auth and auth.is_valid():
            # Si autorisé, retourner le DEP agrégé (similaire à PAT-1)
            notes = ClinicalNoteSerializer(ClinicalNote.objects.filter(patient=patient).order_by('-created_at'), many=True).data
            prescriptions = PrescriptionSerializer(Prescription.objects.filter(patient=patient).order_by('-created_at'), many=True).data
            lab_results = LabTestSerializer(LabTest.objects.filter(patient=patient).order_by('-created_at'), many=True).data
            
            return Response({
                'patient_name': patient.userName,
                'access_status': 'Autorisé',
                'clinical_notes': notes,
                'prescriptions': prescriptions,
                'lab_results': lab_results,
            })
        else:
            return Response({"detail": "Accès non autorisé ou expiré."}, status=HTTP_403_FORBIDDEN)


@extend_schema(tags=["Médecin - Clinique"])
class DoctorClinicalViewSet(GenericViewSet): # Changé ModelViewSet en GenericViewSet car il n'est pas basé sur un seul modèle
    """DOC-4, DOC-5, DOC-6 : Gestion des notes, ordonnances et interprétations."""
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return ClinicalNote.objects.none() 

    def get_serializer_class(self):
        if self.action == 'add_note':
            return ClinicalNoteSerializer
        if self.action == 'create_prescription':
            return PrescriptionSerializer
        if self.action == 'interpret_lab_result':
            return LabTestInterpretationSerializer
        return super().get_serializer_class()

    # /api/dep/doctor/add-note/
    @action(detail=False, methods=['post'], url_path='add-note')
    def add_note(self, request):
        """DOC-4: Ajout de Notes Cliniques."""
        serializer = ClinicalNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        patient_id = request.data.get('patient') # L'ID du patient doit être dans le body
        if not patient_id:
             return Response({"patient": "Le champ patient est requis."}, status=HTTP_400_BAD_REQUEST)

        try:
            patient = User.objects.get(id=patient_id, userRole=User.TypeRole.PATIENT)
        except User.DoesNotExist:
            return Response({"detail": "Patient non trouvé."}, status=HTTP_404_NOT_FOUND)

        auth = AccessAuthorization.objects.filter(patient=patient, professional=request.user, is_active=True).first()
        if not auth or not auth.is_valid():
             return Response({"detail": "Accès au DEP du patient non autorisé ou expiré pour l'écriture."}, status=HTTP_403_FORBIDDEN)
        
        # Sauvegarde de la note
        note = serializer.save(doctor=request.user, patient=patient)
        return Response(ClinicalNoteSerializer(note).data, status=HTTP_201_CREATED)

    # /api/dep/doctor/create-prescription/
    @action(detail=False, methods=['post'], url_path='create-prescription')
    def create_prescription(self, request):
        """DOC-5: Création d'une Ordonnance."""
        serializer = PrescriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        patient_id = request.data.get('patient')
        try:
            patient = User.objects.get(id=patient_id, userRole=User.TypeRole.PATIENT)
        except User.DoesNotExist:
            return Response({"detail": "Patient non trouvé."}, status=HTTP_404_NOT_FOUND)

        auth = AccessAuthorization.objects.filter(patient=patient, professional=request.user, is_active=True).first()
        if not auth or not auth.is_valid():
             return Response({"detail": "Accès au DEP du patient non autorisé ou expiré pour l'écriture."}, status=HTTP_403_FORBIDDEN)
             
        prescription = serializer.save(doctor=request.user, patient=patient)
        return Response(PrescriptionSerializer(prescription).data, status=HTTP_201_CREATED)

    # /api/dep/doctor/interpret-lab-result/{pk}/
    @action(detail=True, methods=['patch'], url_path='interpret-lab-result')
    def interpret_lab_result(self, request, pk=None):
        """DOC-6: Interprétation des Résultats Labo."""
        lab_test = get_object_or_404(LabTest, pk=pk)
        
        auth = AccessAuthorization.objects.filter(patient=lab_test.patient, professional=request.user, is_active=True).first()
        if not auth or not auth.is_valid():
             return Response({"detail": "Accès au DEP du patient non autorisé ou expiré pour l'écriture."}, status=HTTP_403_FORBIDDEN)

        serializer = LabTestInterpretationSerializer(lab_test, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(interpreted_by=request.user)
        
        return Response(LabTestSerializer(lab_test).data, status=HTTP_200_OK)


@extend_schema(tags=["Laboratoire"])
class LabTestViewSet(ModelViewSet):
    """LAB-1, LAB-2, LAB-3 : Gestion des examens et des résultats."""
    permission_classes = [IsLabo]
    serializer_class = LabTestSerializer
    
    # LAB-1: Consulter Examens Prescrits
    def get_queryset(self):
        # Retourne les examens prescrit par un médecin (ou directement) et ciblant ce labo 
        return LabTest.objects.filter(
            Q(performed_by=self.request.user) # Si le labo est explicitement désigné
            | Q(performed_by__isnull=True) # Pour les cas où le labo peut prendre n'importe quel test
        ).order_by('-created_at')

    # /api/dep/labo/examens/{pk}/set-status/
    @action(detail=True, methods=['patch'], url_path='set-status')
    def set_status(self, request, pk=None):
        """LAB-2: Modifier Statut Examen."""
        lab_test = get_object_or_404(LabTest, pk=pk)
        
        if lab_test.performed_by and lab_test.performed_by != request.user:
             return Response({"detail": "Vous n'êtes pas autorisé à modifier cet examen."}, status=HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        if new_status not in [choice[0] for choice in LabTest.TestStatus.choices]:
             return Response({"status": "Statut invalide."}, status=HTTP_400_BAD_REQUEST)
        
        lab_test.status = new_status
        lab_test.save()
        return Response(LabTestSerializer(lab_test).data, status=HTTP_200_OK)

    # /api/dep/labo/examens/{pk}/upload-result/
    @action(detail=True, methods=['post'], parser_classes=[FileUploadParser], url_path='upload-result')
    def upload_result(self, request, pk=None):
        """LAB-3: Dépôt des Résultats."""
        lab_test = get_object_or_404(LabTest, pk=pk)
        
        if lab_test.performed_by and lab_test.performed_by != request.user:
             return Response({"detail": "Vous n'êtes pas autorisé à modifier cet examen."}, status=HTTP_403_FORBIDDEN)

        serializer = LabTestResultUploadSerializer(lab_test, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        lab_test = serializer.save(
            result_uploaded_at=timezone.now(),
            status=LabTest.TestStatus.COMPLETED, 
            performed_by=request.user 
        )
        return Response(LabTestSerializer(lab_test).data, status=HTTP_200_OK)


@extend_schema(tags=["Administrateur - Gestion"])
class AdminControlViewSet(GenericViewSet):
    """ADM-1, ADM-2, ADM-3, ADM-5 : Gestion des comptes et audit."""
    permission_classes = [IsAdminUser]

    # /api/admin/pending-pros/ (ADM-1)
    @action(detail=False, methods=['get'], url_path='pending-pros')
    def list_pending_professionals(self, request):
        """ADM-1: Récupération de la liste des comptes en attente de validation."""
        
        pending_users = User.objects.filter(
            Q(userRole=User.TypeRole.MEDECIN) | Q(userRole=User.TypeRole.LABORATOIRE)
        ).filter(is_active=False).order_by('created_at')

        return Response(UserSerializer(pending_users, many=True).data)

    # /api/admin/validate-pro/{pk}/ (ADM-1)
    @action(detail=True, methods=['patch'])
    def validate_professional(self, request, pk=None):
        """ADM-1: Validation d'un compte professionnel (met is_active à True)."""
        user = get_object_or_404(User, pk=pk)
        if user.userRole in [User.TypeRole.MEDECIN, User.TypeRole.LABORATOIRE] and not user.is_active:
            user.is_active = True
            user.save()
            return Response(UserSerializer(user).data, status=HTTP_200_OK)
        return Response({"detail": "Utilisateur non trouvé ou déjà validé."}, status=HTTP_400_BAD_REQUEST)

    # /api/admin/logs/ (ADM-5)
    @action(detail=False, methods=['get'])
    def audit_logs(self, request):
        """ADM-5: Récupération des journaux d'audit."""
        logs = AuditLog.objects.all().order_by('-timestamp')
        return Response(AuditLogSerializer(logs, many=True).data)