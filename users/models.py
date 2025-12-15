from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils import timezone


class UserManager(BaseUserManager):

    class TypeRole(models.TextChoices):
        PATIENT = "Patient"
        MEDECIN = "Médecin"
        ADMIN = "Admin"
        LABORATOIRE = "Laboratoire"

    def create_user(self, userMail, password=None, **extra_fields):
        if not userMail:
            raise ValueError("L'adresse Mail est obligatoire")

        extra_fields.setdefault("userRole", self.TypeRole.PATIENT)

        user = self.model(userMail=self.normalize_email(userMail), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, userMail, password=None, **extra_fields):

        extra_fields.setdefault("userRole", self.TypeRole.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(userMail, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    class TypeRole(models.TextChoices):
        PATIENT = "Patient"
        MEDECIN = "Médecin"
        ADMIN = "Admin"
        LABORATOIRE = "Laboratoire"

    class TypeGender(models.TextChoices):
        MASCULIN = "M"
        FEMININ = "F"

    userMail = models.EmailField(unique=True, null=False, blank=False)
    userName = models.CharField(max_length=50, null=False)
    userForName = models.CharField(max_length=50, null=False)
    userPhone = models.CharField(max_length=9, null=True, blank=True)
    userDateOfBirth = models.DateField(blank=True, null=True)
    userGender = models.CharField(
        max_length=10, choices=TypeGender.choices, blank=False, null=False
    )
    userAddress = models.TextField(null=True, blank=True)
    userRole = models.CharField(
        max_length=20, choices=TypeRole.choices, default=TypeRole.ADMIN
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "userMail"
    REQUIRED_FIELDS = [
        "userName",
        "userForName",
        "userPhone",
        "userGender",
        "userAddress",
    ]

    def __str__(self):
        return f"{self.userName} ({self.userMail})"


class MedecinProfile(models.Model):
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="medecin_profile"
    )
    hospital = models.CharField(max_length=50, blank=False, null=True)

    def __str__(self):
        return f"MedecinProfile de {self.user.userName}"


class PatientProfile(models.Model):

    class TypeGenotype(models.TextChoices):
        AA = "AA"
        AS = "AS"
        SS = "SS"
        AC = "AC"
        SC = "SC"

    class TypeBloodGroup(models.TextChoices):
        A_POS = "A+"
        A_NEG = "A-"
        B_POS = "B+"
        B_NEG = "B-"
        AB_POS = "AB+"
        AB_NEG = "AB-"
        O_POS = "O+"
        O_NEG = "O-"

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="patient_profile"
    )
    userAllergies = models.TextField(blank=True, null=True)
    userDiseases = models.TextField(blank=True, null=True)
    userGenotype = models.CharField(
        max_length=5,
        null=True,
        blank=True,
        choices=TypeGenotype.choices,
    )
    userBloodGroup = models.CharField(
        max_length=5, choices=TypeBloodGroup.choices, null=False, blank=False
    )

    def __str__(self):
        return f"PatientProfile de {self.user.userName}"


class LaboProfile(models.Model):
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="labo_profile"
    )

    def __str__(self):
        return f"LaboProfile de {self.user.userName}"


class AccessAuthorization(models.Model):
    patient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="granted_accesses"
    )
    # L'utilisateur autorisé (Médecin ou Laboratoire)
    professional = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_accesses"
    )

    granted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # Peut être utilisé pour les accès d'urgence (PAT-6)
    is_emergency = models.BooleanField(default=False) 

    class Meta:
        unique_together = ('patient', 'professional')

    def __str__(self):
        return f"Accès de {self.professional.userName} au DEP de {self.patient.userName}"

    def is_valid(self):
        """Vérifie si l'autorisation est active et non expirée."""
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True


# Modèle pour les Notes Cliniques / Consultations (DOC-4)
class ClinicalNote(models.Model):
    """Enregistre les notes de consultation et les paramètres vitaux."""

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clinical_notes")
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recorded_notes")
    
    # Paramètres de consultation
    tension_arterielle = models.CharField(max_length=15, null=True, blank=True) # Ex: "120/80 mmHg"
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True) # Ex: 37.5
    poids = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Notes, observations et diagnostics
    observation = models.TextField()
    diagnostic = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Note clinique pour {self.patient.userName} par Dr. {self.doctor.userName} le {self.created_at.strftime('%Y-%m-%d')}"


# Modèle pour les Ordonnances (DOC-5)
class Prescription(models.Model):
    """Représente une ordonnance créée par un médecin."""
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prescriptions")
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="issued_prescriptions")
    
    medication_details = models.TextField() # Détails des médicaments et posologies
    
    # Référence au document PDF généré (si vous utilisez le stockage de fichiers)
    pdf_document = models.FileField(upload_to='prescriptions/', null=True, blank=True) 
    
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Ordonnance #{self.id} pour {self.patient.userName}"


# Modèle pour les Examens de Laboratoire (LAB-1, LAB-2, LAB-3)
class LabTest(models.Model):
    """Représente un examen de laboratoire prescrit et son résultat."""

    class TestStatus(models.TextChoices):
        PENDING = "En attente"
        IN_PROGRESS = "En cours"
        COMPLETED = "Terminé"
        CANCELED = "Annulé"

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lab_tests")
    
    # L'examen peut être prescrit par un médecin ou être direct
    prescribed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="prescribed_tests"
    )
    # Le laboratoire qui effectue l'examen
    performed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="performed_tests"
    )
    
    test_name = models.CharField(max_length=100)
    details = models.TextField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20, choices=TestStatus.choices, default=TestStatus.PENDING
    )
    
    # Résultat (document déposé par le labo)
    result_document = models.FileField(upload_to='lab_results/', null=True, blank=True)
    result_uploaded_at = models.DateTimeField(null=True, blank=True)
    
    # Interprétation du médecin (DOC-6)
    doctor_interpretation = models.TextField(null=True, blank=True)
    interpreted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="interpreted_tests"
    )
    
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.test_name} - Statut: {self.status} pour {self.patient.userName}"


# Modèle pour les journaux d'audit (ADM-5, AUTH-1)
class AuditLog(models.Model):
    """Enregistre les actions critiques (connexion, accès DEP, modification de données)."""
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255) # Ex: "Connexion réussie", "Accès DEP Patient 123", "Modification Profil"
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user.userMail if self.user else 'N/A'} - {self.action}"
