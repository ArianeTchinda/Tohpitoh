from cProfile import label
import attr
from rest_framework.serializers import (
    ModelSerializer,
    CharField,
    Serializer,
    ChoiceField,
)
from rest_framework.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import models
from users.models import User, PatientProfile, MedecinProfile, LaboProfile, AuditLog , ClinicalNote, Prescription, LabTest, AccessAuthorization


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "userMail",
            "userName",
            "userForName",
            "userPhone",
            "userDateOfBirth",
            "userGender",
            "userAddress",
            "userRole",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserRegisterSerializer(ModelSerializer):
    password = CharField(write_only=True, required=True)
    password2 = CharField(write_only=True, required=True, label="Confirm password")

    class Meta:
        model = User
        fields = [
            "userMail",
            "userName",
            "userForName",
            "userPhone",
            "userDateOfBirth",
            "userGender",
            "userAddress",
            "userRole",
            "password",
            "password2",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise ValidationError(
                {"password": "Les mots de passe ne correspondent pas."}
            )
        validate_password(attrs["password"])

        userRole = attrs.get("userRole")
        valid_roles = [choice[0] for choice in User.TypeRole.choices]
        if userRole not in valid_roles:
            raise ValidationError({"userRole": "Rôle invalide"})
        if userRole == User.TypeRole.ADMIN:
            raise ValidationError(
                {"userRole": "L'inscription en tant qu'admin n'est pas autorisée."}
            )

        userMail = attrs.get("userMail")
        if User.objects.filter(userMail__iexact=userMail).exists():
            raise ValidationError({"userMail": "Cet email est déjà utilisé."})

        userGender = attrs.get("userGender")
        valid_genders = [choice[0] for choice in User.TypeGender.choices]
        if userGender not in valid_genders:
            raise ValidationError({"userGender": "Genre invalide"})

        return attrs

    def create(self, validated_data):
        validated_data["userMail"] = validated_data["userMail"].lower()
        
        # *** CORRECTION CRITIQUE 1/4 ***
        # Utiliser create_user pour hacher correctement le mot de passe
        password = validated_data.pop("password")
        validated_data.pop("password2")
        
        user = User.objects.create_user(
            password=password, 
            **validated_data
        )
        # Fin de la correction
        
        return user


class UserUpdateSerializer(ModelSerializer):
    class Meta:
        model = User
        exclude = ["password"]


class ChangePasswordSerializer(Serializer):
    old_password = CharField(required=True)
    new_password = CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)

        return value


class PatientRegisterSerializer(UserRegisterSerializer):
    userBloodGroup = ChoiceField(choices=PatientProfile.TypeBloodGroup.choices)
    userGenotype = ChoiceField(
        choices=PatientProfile.TypeGenotype.choices, required=False, allow_null=True
    )
    userDiseases = CharField(required=False, allow_blank=True)
    userAllergies = CharField(required=False, allow_blank=True)

    class Meta(UserRegisterSerializer.Meta):
        fields = UserRegisterSerializer.Meta.fields + [
            "userBloodGroup",
            "userGenotype",
            "userDiseases",
            "userAllergies",
        ]

    def validate(self, attrs):
        attrs["userRole"] = User.TypeRole.PATIENT
        return super().validate(attrs)

    def create(self, validated_data):
        # 1. Extraire les champs spécifiques au profil
        blood_group = validated_data.pop("userBloodGroup")
        genotype = validated_data.pop("userGenotype")
        diseases = validated_data.pop("userDiseases", None)
        allergies = validated_data.pop("userAllergies", None)
        
        # 2. Extraire et préparer les données d'utilisateur
        validated_data["userMail"] = validated_data["userMail"].lower()
        password = validated_data.pop("password")
        validated_data.pop("password2")
        
        # *** CORRECTION CRITIQUE 2/4 ***
        # Création de l'utilisateur de base (hachage du mot de passe inclus)
        user = User.objects.create_user(password=password, **validated_data)
        # Fin de la correction
        
        # 3. Création du profil patient
        PatientProfile.objects.create(
            user=user,
            userBloodGroup=blood_group,
            userGenotype=genotype,
            userDiseases=diseases,
            userAllergies=allergies,
        )

        return user


class LaboRegisterSerializer(UserRegisterSerializer):

    def validate(self, attrs):
        attrs["userRole"] = User.TypeRole.LABORATOIRE
        return super().validate(attrs)

    def create(self, validated_data):
        
        # 1. Extraire et préparer les données d'utilisateur
        validated_data["userMail"] = validated_data["userMail"].lower()
        password = validated_data.pop("password")
        validated_data.pop("password2")

        # *** CORRECTION CRITIQUE 3/4 ***
        # Création de l'utilisateur de base (hachage du mot de passe inclus)
        user = User.objects.create_user(password=password, **validated_data)
        # Fin de la correction
        
        # 2. Création du profil spécifique
        LaboProfile.objects.create(user=user)

        return user


class MedecinRegisterSerializer(UserRegisterSerializer):
    hospital = CharField(required=False, allow_blank=True, allow_null=True)

    class Meta(UserRegisterSerializer.Meta):
        fields = UserRegisterSerializer.Meta.fields + ["hospital"]

    def validate(self, attrs):
        attrs["userRole"] = User.TypeRole.MEDECIN
        return super().validate(attrs)

    def create(self, validated_data):
        # 1. Extraire les champs spécifiques au profil
        hospital = validated_data.pop("hospital", None)

        # 2. Extraire et préparer les données d'utilisateur
        validated_data["userMail"] = validated_data["userMail"].lower()
        password = validated_data.pop("password")
        validated_data.pop("password2")

        # *** CORRECTION CRITIQUE 4/4 ***
        # Création de l'utilisateur de base (hachage du mot de passe inclus)
        user = User.objects.create_user(password=password, **validated_data)
        # Fin de la correction

        # 3. Création du profil spécifique
        MedecinProfile.objects.create(user=user, hospital=hospital)

        return user


class AccessAuthorizationSerializer(ModelSerializer):
    patient_name = CharField(source='patient.userName', read_only=True)
    professional_name = CharField(source='professional.userName', read_only=True)
    
    class Meta:
        model = AccessAuthorization
        fields = [
            'id', 'patient', 'professional', 'granted_at', 'expires_at', 
            'is_active', 'is_emergency', 'patient_name', 'professional_name'
        ]
        read_only_fields = ['id', 'granted_at', 'is_active', 'patient_name', 'professional_name', 'is_emergency']

# Sérialiseur pour créer une demande d'accès
class CreateAccessRequestSerializer(Serializer):
    professional_email = CharField(required=True)
    expiration_days = models.IntegerField(default=7) # Durée de l'accès

# Sérialiseur pour les Notes Cliniques (DOC-4)
class ClinicalNoteSerializer(ModelSerializer):
    doctor_name = CharField(source='doctor.userName', read_only=True)
    
    class Meta:
        model = ClinicalNote
        fields = '__all__'
        read_only_fields = ['id', 'patient', 'doctor', 'created_at', 'doctor_name']

# Sérialiseur pour les Ordonnances (DOC-5)
class PrescriptionSerializer(ModelSerializer):
    doctor_name = CharField(source='doctor.userName', read_only=True)
    
    class Meta:
        model = Prescription
        fields = '__all__'
        read_only_fields = ['id', 'patient', 'doctor', 'created_at', 'pdf_document', 'doctor_name']

# Sérialiseur pour les Examens de Laboratoire (LAB-1, LAB-3)
class LabTestSerializer(ModelSerializer):
    patient_name = CharField(source='patient.userName', read_only=True)
    prescribed_by_name = CharField(source='prescribed_by.userName', read_only=True)
    performed_by_name = CharField(source='performed_by.userName', read_only=True)
    interpreted_by_name = CharField(source='interpreted_by.userName', read_only=True)
    
    class Meta:
        model = LabTest
        fields = '__all__'
        read_only_fields = ['id', 'patient', 'created_at', 'result_uploaded_at', 'patient_name', 'prescribed_by_name', 'performed_by_name', 'interpreted_by_name']
        
# Sérialiseur d'upload de résultat (LAB-3)
class LabTestResultUploadSerializer(ModelSerializer):
    class Meta:
        model = LabTest
        fields = ['result_document', 'status']

    def validate_result_document(self, value):
        if not value:
            raise ValidationError("Le document de résultat est obligatoire.")
        return value

# Sérialiseur d'Interprétation (DOC-6)
class LabTestInterpretationSerializer(ModelSerializer):
    class Meta:
        model = LabTest
        fields = ['doctor_interpretation']

# Sérialiseur de Log d'Audit (ADM-5)
class AuditLogSerializer(ModelSerializer):
    user_email = CharField(source='user.userMail', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['id', 'user', 'timestamp', 'ip_address']
