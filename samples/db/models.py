from datetime import date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import UniqueConstraint

from backend.app.db.base import Base


class Person(Base):
    __tablename__ = "person"
    __table_args__ = (
        CheckConstraint(
            "gender IS NULL OR gender IN ('MALE', 'FEMALE', 'OTHER', 'UNKNOWN')",
            name="chk_person_gender",
        ),
    )

    person_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)
    profile_image_url: Mapped[str | None] = mapped_column(Text)
    remark: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gender: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[date | None] = mapped_column(Date)
    email: Mapped[str | None] = mapped_column(String(255))

    roles: Mapped[list["PersonRole"]] = relationship(back_populates="person")
    statuses: Mapped[list["PersonStatus"]] = relationship(back_populates="person")
    caregiver_profile: Mapped["CaregiverProfile | None"] = relationship(back_populates="person")
    patient_profile: Mapped["PatientProfile | None"] = relationship(back_populates="person")
    fc_profile: Mapped["FcProfile | None"] = relationship(back_populates="person")


class PersonRole(Base):
    __tablename__ = "person_role"
    __table_args__ = (
        UniqueConstraint("person_id", "role_type", name="uq_person_role"),
        CheckConstraint("role_type IN ('CAREGIVER', 'PATIENT', 'FC', 'GUARDIAN')", name="chk_person_role_type"),
    )

    person_role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.person_id"), nullable=False)
    role_type: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    person: Mapped[Person] = relationship(back_populates="roles")


class PersonStatus(Base):
    __tablename__ = "person_status"
    __table_args__ = (
        CheckConstraint(
            "status_code IS NULL OR status_code IN "
            "('ACTIVE', 'INACTIVE', 'ON_HOLD', 'BLACKLISTED', 'ON_LEAVE', 'TERMINATED')",
            name="chk_person_status_code",
        ),
        UniqueConstraint("person_id", "is_current", name="uq_person_status_current"),
    )

    person_status_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey(
            "person.person_id",
            name="fk_person_status_person",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    status_label: Mapped[str] = mapped_column(String(50), nullable=False)
    status_code: Mapped[str | None] = mapped_column(String(50))
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    person: Mapped[Person] = relationship(back_populates="statuses")


class CaregiverProfile(Base):
    __tablename__ = "caregiver_profile"
    __table_args__ = (
        CheckConstraint(
            "caregiver_status IN ('ACTIVE', 'INACTIVE', 'ON_HOLD', 'BLACKLISTED')",
            name="chk_caregiver_profile_status",
        ),
    )

    caregiver_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.person_id"), unique=True, nullable=False)
    member_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    registered_at: Mapped[date] = mapped_column(Date, nullable=False)
    caregiver_status: Mapped[str] = mapped_column(String(30), nullable=False)
    average_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, default=0)
    rating_count: Mapped[int] = mapped_column(nullable=False, default=0)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    specialties: Mapped[str | None] = mapped_column(Text)

    person: Mapped[Person] = relationship(back_populates="caregiver_profile")
    tags: Mapped[list["CaregiverTag"]] = relationship(back_populates="caregiver")


class CaregiverTag(Base):
    __tablename__ = "caregiver_tag"
    __table_args__ = (UniqueConstraint("caregiver_id", "tag_name", name="uq_caregiver_tag_caregiver_name"),)

    caregiver_tag_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    caregiver_id: Mapped[int] = mapped_column(ForeignKey("caregiver_profile.caregiver_id"), nullable=False)
    tag_name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    caregiver: Mapped[CaregiverProfile] = relationship(back_populates="tags")


class FcProfile(Base):
    __tablename__ = "fc_profile"
    __table_args__ = (
        CheckConstraint(
            "fc_status IN ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED')",
            name="chk_fc_profile_status",
        ),
    )

    fc_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.person_id"), unique=True, nullable=False)
    organization: Mapped[str | None] = mapped_column(String(100))
    fc_status: Mapped[str] = mapped_column(String(30), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    person: Mapped[Person] = relationship(back_populates="fc_profile")
    patients: Mapped[list["PatientProfile"]] = relationship(back_populates="primary_fc")


class PatientProfile(Base):
    __tablename__ = "patient_profile"
    __table_args__ = (
        CheckConstraint(
            "guardian_relationship IS NULL OR guardian_relationship IN "
            "('SPOUSE', 'CHILD', 'PARENT', 'SIBLING', 'RELATIVE', 'LEGAL_GUARDIAN', 'OTHER')",
            name="chk_patient_profile_guardian_relationship",
        ),
    )

    patient_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.person_id"), unique=True, nullable=False)
    registration_source: Mapped[str | None] = mapped_column(String(50))
    primary_fc_id: Mapped[int | None] = mapped_column(ForeignKey("fc_profile.fc_id"))
    guardian_name: Mapped[str | None] = mapped_column(String(100))
    guardian_relationship: Mapped[str | None] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    person: Mapped[Person] = relationship(back_populates="patient_profile")
    primary_fc: Mapped[FcProfile | None] = relationship(back_populates="patients")
    care_profile: Mapped["PatientCareProfile | None"] = relationship(back_populates="patient")


class PatientCareProfile(Base):
    __tablename__ = "patient_care_profile"
    __table_args__ = (
        CheckConstraint(
            "default_mobility_level IS NULL OR default_mobility_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH')",
            name="chk_patient_care_profile_default_mobility_level",
        ),
        CheckConstraint(
            "default_dementia_level IS NULL OR default_dementia_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH')",
            name="chk_patient_care_profile_default_dementia_level",
        ),
        CheckConstraint(
            "default_toileting_level IS NULL OR default_toileting_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH')",
            name="chk_patient_care_profile_default_toileting_level",
        ),
        CheckConstraint(
            "default_meal_assistance_level IS NULL OR default_meal_assistance_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH')",
            name="chk_patient_care_profile_default_meal_assistance_level",
        ),
        CheckConstraint(
            "default_preferred_caregiver_gender IS NULL OR default_preferred_caregiver_gender IN "
            "('MALE', 'FEMALE', 'ANY')",
            name="chk_patient_care_profile_default_preferred_caregiver_gender",
        ),
        CheckConstraint(
            "default_care_intensity_level IS NULL OR default_care_intensity_level IN ('LOW', 'MEDIUM', 'HIGH')",
            name="chk_patient_care_profile_default_care_intensity_level",
        ),
    )

    patient_care_profile_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey(
            "patient_profile.patient_id",
            name="fk_patient_care_profile_patient",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        unique=True,
        nullable=False,
    )
    default_disease_note: Mapped[str | None] = mapped_column(Text)
    default_mobility_level: Mapped[str | None] = mapped_column(String(30))
    default_dementia_level: Mapped[str | None] = mapped_column(String(30))
    default_toileting_level: Mapped[str | None] = mapped_column(String(30))
    default_meal_assistance_level: Mapped[str | None] = mapped_column(String(30))
    default_medication_note: Mapped[str | None] = mapped_column(Text)
    default_special_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    default_medication_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_rehab_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_suction_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_night_care_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_infection_precaution_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_preferred_caregiver_gender: Mapped[str | None] = mapped_column(String(20))
    default_allergy_note: Mapped[str | None] = mapped_column(String(255))
    default_care_intensity_level: Mapped[str | None] = mapped_column(String(20))

    patient: Mapped[PatientProfile] = relationship(back_populates="care_profile")


class FcPatientRelation(Base):
    __tablename__ = "fc_patient_relation"

    fc_patient_relation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fc_id: Mapped[int] = mapped_column(ForeignKey("fc_profile.fc_id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profile.patient_id"), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Hospital(Base):
    __tablename__ = "hospital"
    __table_args__ = (
        Index("idx_hospital_name", "hospital_name"),
        Index("idx_hospital_phone", "phone", postgresql_where=text("phone IS NOT NULL")),
    )

    hospital_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    hospital_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(30))
    remark: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FileAsset(Base):
    __tablename__ = "file_asset"
    __table_args__ = (
        Index("idx_file_asset_created_at", "created_at"),
        Index("uq_file_asset_storage_key", "storage_key", unique=True),
    )

    file_asset_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    operation_documents: Mapped[list["OperationDocument"]] = relationship(back_populates="file_asset")


class OperationDocument(Base):
    __tablename__ = "operation_document"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('CENTER_GUIDE', 'HOSPITAL_GUIDE', 'BUSINESS_LICENSE')",
            name="chk_operation_document_type",
        ),
        CheckConstraint(
            "(is_embedding_enabled = false AND datafication_status IS NULL) "
            "OR (is_embedding_enabled = true AND datafication_status IN ('PENDING', 'SUCCESS', 'FAILED'))",
            name="chk_operation_document_datafication_status",
        ),
        CheckConstraint(
            "(document_type = 'HOSPITAL_GUIDE' AND hospital_id IS NOT NULL) "
            "OR (document_type <> 'HOSPITAL_GUIDE' AND hospital_id IS NULL)",
            name="chk_operation_document_hospital_required",
        ),
        Index("idx_operation_document_type", "document_type"),
        Index("idx_operation_document_hospital_id", "hospital_id"),
        Index("idx_operation_document_datafication_status", "datafication_status"),
        Index("idx_operation_document_updated_at", "updated_at"),
    )

    operation_document_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    hospital_id: Mapped[int | None] = mapped_column(ForeignKey("hospital.hospital_id"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text)
    file_asset_id: Mapped[int | None] = mapped_column(ForeignKey("file_asset.file_asset_id"))
    datafication_status: Mapped[str | None] = mapped_column(String(20))
    datafication_error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_embedding_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    file_asset: Mapped[FileAsset | None] = relationship(back_populates="operation_documents")
    vectors: Mapped[list["OperationDocumentVector"]] = relationship(back_populates="operation_document")


class OperationDocumentVector(Base):
    __tablename__ = "operation_document_vector"
    __table_args__ = (
        UniqueConstraint("operation_document_id", "chunk_index", name="uq_operation_document_vector_chunk"),
        Index("idx_operation_document_vector_document_id", "operation_document_id"),
        Index(
            "idx_operation_document_vector_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    operation_document_vector_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    operation_document_id: Mapped[int] = mapped_column(
        ForeignKey(
            "operation_document.operation_document_id",
            name="fk_operation_document_vector_document",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    content_hash: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    operation_document: Mapped[OperationDocument] = relationship(back_populates="vectors")


class MatchingRequest(Base):
    __tablename__ = "matching_request"
    __table_args__ = (
        CheckConstraint(
            "request_status IN ("
            "'REQUESTED', 'RECOMMENDING', 'RECOMMENDED', 'ASSIGNING', "
            "'CONTRACT_PENDING', 'COMPLETED', 'CANCELED'"
            ")",
            name="chk_matching_request_status",
        ),
        CheckConstraint(
            "care_location_type IN ('HOSPITAL', 'HOME', 'FACILITY', 'OTHER')",
            name="chk_matching_request_care_location_type",
        ),
        CheckConstraint(
            "requester_relationship_snapshot IS NULL OR requester_relationship_snapshot IN "
            "('SELF', 'SPOUSE', 'CHILD', 'PARENT', 'SIBLING', 'RELATIVE', 'LEGAL_GUARDIAN', 'OTHER', 'UNKNOWN')",
            name="chk_matching_request_requester_relationship_snapshot",
        ),
        CheckConstraint(
            "patient_gender_snapshot IS NULL OR patient_gender_snapshot IN ('MALE', 'FEMALE', 'OTHER', 'UNKNOWN')",
            name="chk_matching_request_patient_gender_snapshot",
        ),
        CheckConstraint(
            "requester_type IS NULL OR requester_type IN ('PATIENT', 'GUARDIAN', 'FC', 'OTHER', 'UNKNOWN')",
            name="chk_matching_request_requester_type",
        ),
        Index("idx_matching_request_care_location_type", "care_location_type"),
        Index("idx_matching_request_hospital_id", "hospital_id"),
        Index("idx_matching_request_patient_id", "patient_id"),
        Index("idx_matching_request_proposed_start_datetime", "proposed_start_datetime"),
        Index("idx_matching_request_received_by_fc_id", "received_by_fc_id"),
        Index("idx_matching_request_requester_person_id", "requester_person_id"),
        Index("idx_matching_request_status", "request_status"),
    )

    matching_request_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "patient_profile.patient_id",
            name="fk_matching_request_patient",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    received_by_fc_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "fc_profile.fc_id",
            name="fk_matching_request_received_by_fc",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    request_status: Mapped[str] = mapped_column(String(40), nullable=False)
    care_location_type: Mapped[str] = mapped_column(String(30), nullable=False)
    hospital_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "hospital.hospital_id",
            name="fk_matching_request_hospital",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    hospital_room: Mapped[str | None] = mapped_column(String(50))
    proposed_start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    proposed_end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposed_daily_wage: Mapped[Decimal | None] = mapped_column(Numeric(12))
    requester_name_snapshot: Mapped[str | None] = mapped_column(String(100))
    requester_relationship_snapshot: Mapped[str | None] = mapped_column(String(50))
    patient_name_snapshot: Mapped[str | None] = mapped_column(String(100))
    patient_gender_snapshot: Mapped[str | None] = mapped_column(String(20))
    patient_birth_date_snapshot: Mapped[date | None] = mapped_column(Date)
    requester_person_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "person.person_id",
            name="fk_matching_request_requester_person",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    hospital_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    requester_type: Mapped[str | None] = mapped_column(String(30))
    requester_phone_snapshot: Mapped[str | None] = mapped_column(String(30))
    care_request_reason: Mapped[str | None] = mapped_column(Text)
    request_memo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MatchingRequestRequirement(Base):
    __tablename__ = "matching_request_requirement"
    __table_args__ = (
        UniqueConstraint(
            "matching_request_id",
            name="matching_request_requirement_matching_request_id_key",
        ),
        CheckConstraint(
            "mobility_level IS NULL OR mobility_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH')",
            name="chk_matching_request_requirement_mobility_level",
        ),
        CheckConstraint(
            "dementia_level IS NULL OR dementia_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH')",
            name="chk_matching_request_requirement_dementia_level",
        ),
        CheckConstraint(
            "toileting_level IS NULL OR toileting_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH')",
            name="chk_matching_request_requirement_toileting_level",
        ),
        CheckConstraint(
            "meal_assistance_level IS NULL OR meal_assistance_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH')",
            name="chk_matching_request_requirement_meal_assistance_level",
        ),
        CheckConstraint(
            "preferred_caregiver_gender IS NULL OR preferred_caregiver_gender IN ('MALE', 'FEMALE', 'ANY')",
            name="chk_matching_request_requirement_preferred_caregiver_gender",
        ),
        CheckConstraint(
            "care_intensity_level IS NULL OR care_intensity_level IN ('LOW', 'MEDIUM', 'HIGH')",
            name="chk_matching_request_requirement_care_intensity_level",
        ),
    )

    matching_request_requirement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    matching_request_id: Mapped[int] = mapped_column(
        ForeignKey(
            "matching_request.matching_request_id",
            name="fk_matching_request_requirement_request",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    disease_note: Mapped[str | None] = mapped_column(Text)
    allergy_note: Mapped[str | None] = mapped_column(String(255))
    mobility_level: Mapped[str | None] = mapped_column(String(30))
    dementia_level: Mapped[str | None] = mapped_column(String(30))
    toileting_level: Mapped[str | None] = mapped_column(String(30))
    meal_assistance_level: Mapped[str | None] = mapped_column(String(30))
    medication_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    rehab_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    suction_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    night_care_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    infection_precaution_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    preferred_caregiver_gender: Mapped[str | None] = mapped_column(String(20))
    care_intensity_level: Mapped[str | None] = mapped_column(String(20))
    preferred_conditions_json: Mapped[dict | None] = mapped_column(JSONB)
    care_instruction_json: Mapped[dict | None] = mapped_column(JSONB)
    special_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MatchingRecommendation(Base):
    __tablename__ = "matching_recommendation"
    __table_args__ = (
        UniqueConstraint("matching_request_id", "caregiver_id", name="uq_matching_recommendation_request_caregiver"),
        UniqueConstraint("matching_request_id", "recommendation_rank", name="uq_matching_recommendation_request_rank"),
        CheckConstraint("recommendation_rank BETWEEN 1 AND 3", name="chk_matching_recommendation_rank"),
        CheckConstraint(
            "match_score IS NULL OR match_score BETWEEN 0 AND 100",
            name="chk_matching_recommendation_match_score",
        ),
        CheckConstraint(
            "recommendation_status IN ('RECOMMENDED', 'CONTACTED', 'SELECTED', 'EXCLUDED', 'FAILED')",
            name="chk_matching_recommendation_status",
        ),
        Index("idx_matching_recommendation_call_log_id", "call_log_id"),
        Index("idx_matching_recommendation_caregiver_id", "caregiver_id"),
        Index("idx_matching_recommendation_request_id", "matching_request_id"),
        Index("idx_matching_recommendation_request_rank", "matching_request_id", "recommendation_rank"),
        Index("idx_matching_recommendation_status", "recommendation_status"),
    )

    matching_recommendation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    matching_request_id: Mapped[int] = mapped_column(
        ForeignKey(
            "matching_request.matching_request_id",
            name="fk_matching_recommendation_request",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    caregiver_id: Mapped[int] = mapped_column(
        ForeignKey(
            "caregiver_profile.caregiver_id",
            name="fk_matching_recommendation_caregiver",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    recommendation_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    match_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    recommendation_reason_json: Mapped[dict | None] = mapped_column(JSONB)
    caregiver_snapshot_json: Mapped[dict | None] = mapped_column(JSONB)
    recommendation_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="RECOMMENDED",
        server_default=text("'RECOMMENDED'"),
    )
    call_log_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "call_log.call_log_id",
            name="fk_matching_recommendation_call_log",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    excluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TemporaryAssignment(Base):
    __tablename__ = "temporary_assignment"
    __table_args__ = (
        CheckConstraint(
            "temporary_assignment_status IN ("
            "'PROPOSED', 'HOLDING', 'CAREGIVER_ACCEPTED', 'CAREGIVER_REJECTED', "
            "'PATIENT_ACCEPTED', 'PATIENT_REJECTED', 'CONFIRMED', 'EXPIRED', 'CANCELED'"
            ")",
            name="chk_temporary_assignment_status",
        ),
        Index("idx_temporary_assignment_assigned_by_fc_id", "assigned_by_fc_id"),
        Index("idx_temporary_assignment_caregiver_id", "caregiver_id"),
        Index("idx_temporary_assignment_matching_request_id", "matching_request_id"),
        Index("idx_temporary_assignment_proposed_start_datetime", "proposed_start_datetime"),
        Index("idx_temporary_assignment_status", "temporary_assignment_status"),
    )

    temporary_assignment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    matching_request_id: Mapped[int] = mapped_column(
        ForeignKey(
            "matching_request.matching_request_id",
            name="fk_temporary_assignment_matching_request",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    caregiver_id: Mapped[int] = mapped_column(
        ForeignKey(
            "caregiver_profile.caregiver_id",
            name="fk_temporary_assignment_caregiver",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    assigned_by_fc_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "fc_profile.fc_id",
            name="fk_temporary_assignment_assigned_by_fc",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    temporary_assignment_status: Mapped[str] = mapped_column(String(40), nullable=False)
    proposed_start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    proposed_end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposed_daily_wage: Mapped[Decimal | None] = mapped_column(Numeric(12))
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    caregiver_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    memo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Contract(Base):
    __tablename__ = "contract"
    __table_args__ = (
        CheckConstraint(
            "contract_status IN ('DRAFT', 'PENDING_SIGNATURE', 'SIGNED', 'ACTIVE', 'ENDED', 'CANCELED')",
            name="chk_contract_status",
        ),
        Index("idx_contract_caregiver_id", "caregiver_id"),
        Index("idx_contract_contract_number", "contract_number"),
        Index("idx_contract_fc_id", "fc_id"),
        Index("idx_contract_file_asset_id", "contract_file_asset_id"),
        Index("idx_contract_matching_request_id", "matching_request_id"),
        Index("idx_contract_patient_id", "patient_id"),
        Index("idx_contract_start_datetime", "start_datetime"),
        Index("idx_contract_status", "contract_status"),
        Index("idx_contract_temporary_assignment_id", "temporary_assignment_id"),
    )

    contract_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    contract_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    matching_request_id: Mapped[int] = mapped_column(ForeignKey("matching_request.matching_request_id"), nullable=False)
    temporary_assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("temporary_assignment.temporary_assignment_id")
    )
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profile.patient_id"), nullable=False)
    caregiver_id: Mapped[int] = mapped_column(ForeignKey("caregiver_profile.caregiver_id"), nullable=False)
    fc_id: Mapped[int | None] = mapped_column(ForeignKey("fc_profile.fc_id"))
    contract_status: Mapped[str] = mapped_column(String(30), nullable=False)
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    daily_wage: Mapped[Decimal] = mapped_column(Numeric(12), nullable=False)
    hospital_id: Mapped[int | None] = mapped_column(ForeignKey("hospital.hospital_id"))
    hospital_room: Mapped[str | None] = mapped_column(String(50))
    requirement_snapshot_json: Mapped[dict | None] = mapped_column(JSONB)
    contract_terms_snapshot_json: Mapped[dict | None] = mapped_column(JSONB)
    contract_file_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "file_asset.file_asset_id",
            name="fk_contract_file_asset",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CareService(Base):
    __tablename__ = "care_service"
    __table_args__ = (
        CheckConstraint(
            "service_status IN ('PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELED')",
            name="chk_care_service_status",
        ),
        CheckConstraint(
            "care_location_type IN ('HOSPITAL', 'HOME', 'FACILITY', 'OTHER')",
            name="chk_care_service_care_location_type",
        ),
        CheckConstraint(
            "planned_end_datetime IS NULL OR planned_end_datetime >= planned_start_datetime",
            name="chk_care_service_planned_datetime_range",
        ),
        CheckConstraint(
            "actual_end_datetime IS NULL OR actual_start_datetime IS NULL OR actual_end_datetime >= actual_start_datetime",
            name="chk_care_service_actual_datetime_range",
        ),
        CheckConstraint(
            "daily_wage IS NULL OR daily_wage >= 0",
            name="chk_care_service_daily_wage_non_negative",
        ),
        CheckConstraint(
            "care_location_type <> 'HOSPITAL' "
            "OR hospital_id IS NOT NULL "
            "OR NULLIF(BTRIM(hospital_name_snapshot), '') IS NOT NULL",
            name="chk_care_service_hospital_info_required",
        ),
        Index("idx_care_service_actual_start_datetime", "actual_start_datetime"),
        Index("idx_care_service_caregiver_id", "caregiver_id"),
        Index("idx_care_service_hospital_id", "hospital_id", postgresql_where=text("hospital_id IS NOT NULL")),
        Index("idx_care_service_location_type", "care_location_type"),
        Index("idx_care_service_managed_by_fc_id", "managed_by_fc_id", postgresql_where=text("managed_by_fc_id IS NOT NULL")),
        Index("idx_care_service_patient_id", "patient_id"),
        Index("idx_care_service_planned_start_datetime", "planned_start_datetime"),
        Index("idx_care_service_status", "service_status"),
        Index("idx_care_service_status_planned_start", "service_status", text("planned_start_datetime DESC")),
    )

    care_service_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey(
            "patient_profile.patient_id",
            name="fk_care_service_patient",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    caregiver_id: Mapped[int] = mapped_column(
        ForeignKey(
            "caregiver_profile.caregiver_id",
            name="fk_care_service_caregiver",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    managed_by_fc_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "fc_profile.fc_id",
            name="fk_care_service_managed_by_fc",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    service_status: Mapped[str] = mapped_column(String(30), nullable=False)
    care_location_type: Mapped[str] = mapped_column(String(30), nullable=False)
    hospital_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "hospital.hospital_id",
            name="fk_care_service_hospital",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    hospital_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    hospital_room: Mapped[str | None] = mapped_column(String(50))
    service_address: Mapped[str | None] = mapped_column(Text)
    daily_wage: Mapped[Decimal | None] = mapped_column(Numeric(12, 0))
    planned_start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    planned_end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_start_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    links: Mapped[list["CareServiceLink"]] = relationship(
        back_populates="care_service",
        cascade="all, delete-orphan",
    )


class CareServiceLink(Base):
    __tablename__ = "care_service_link"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(matching_request_id, temporary_assignment_id, contract_id) = 1",
            name="chk_care_service_link_one_target",
        ),
        Index("idx_care_service_link_care_service_id", "care_service_id"),
        Index(
            "idx_care_service_link_matching_request_id",
            "matching_request_id",
            postgresql_where=text("matching_request_id IS NOT NULL"),
        ),
        Index(
            "idx_care_service_link_temporary_assignment_id",
            "temporary_assignment_id",
            postgresql_where=text("temporary_assignment_id IS NOT NULL"),
        ),
        Index("idx_care_service_link_contract_id", "contract_id", postgresql_where=text("contract_id IS NOT NULL")),
        Index("uq_care_service_link_contract", "contract_id", unique=True, postgresql_where=text("contract_id IS NOT NULL")),
    )

    care_service_link_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    care_service_id: Mapped[int] = mapped_column(
        ForeignKey(
            "care_service.care_service_id",
            name="fk_care_service_link_care_service",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    matching_request_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "matching_request.matching_request_id",
            name="fk_care_service_link_matching_request",
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    temporary_assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "temporary_assignment.temporary_assignment_id",
            name="fk_care_service_link_temporary_assignment",
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    contract_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "contract.contract_id",
            name="fk_care_service_link_contract",
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    memo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    care_service: Mapped[CareService] = relationship(back_populates="links")
    matching_request: Mapped[MatchingRequest | None] = relationship()
    temporary_assignment: Mapped[TemporaryAssignment | None] = relationship()
    contract: Mapped[Contract | None] = relationship()


class Review(Base):
    __tablename__ = "review"
    __table_args__ = (
        UniqueConstraint("care_service_id", name="uq_review_care_service"),
        CheckConstraint(
            "review_source IS NULL OR review_source IN ('SURVEY', 'CALL', 'SMS', 'KAKAO', 'MANUAL')",
            name="chk_review_source",
        ),
        CheckConstraint(
            "review_status IN ('REQUEST_PENDING', 'REQUEST_SENT', 'REVIEW_RECEIVED', 'COMPLETED')",
            name="chk_review_status",
        ),
        CheckConstraint(
            "ai_score IS NULL OR ai_score BETWEEN 0 AND 5",
            name="chk_review_ai_score",
        ),
        Index("idx_review_ai_score", "ai_score"),
        Index("idx_review_care_service_id", "care_service_id"),
        Index("idx_review_created_at", "created_at"),
        Index("idx_review_review_source", "review_source"),
        Index("idx_review_reviewer_person_id", "reviewer_person_id"),
        Index("idx_review_status", "review_status"),
        Index("idx_review_status_completed_at", "review_status", "completed_at"),
        Index("idx_review_status_requested_at", "review_status", "requested_at"),
        Index("idx_review_status_submitted_at", "review_status", "submitted_at"),
        Index("uq_review_survey_token", "survey_token", unique=True, postgresql_where=text("survey_token IS NOT NULL")),
    )

    review_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    care_service_id: Mapped[int] = mapped_column(
        ForeignKey(
            "care_service.care_service_id",
            name="fk_review_care_service",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    reviewer_person_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "person.person_id",
            name="fk_review_reviewer_person",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    raw_message: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    review_source: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    review_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="REQUEST_PENDING",
        server_default=text("'REQUEST_PENDING'"),
    )
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    survey_token: Mapped[str | None] = mapped_column(String(100))
    survey_url: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_recommended: Mapped[bool | None] = mapped_column(Boolean)
    keyword_json: Mapped[dict | None] = mapped_column(JSONB)
    reply_message: Mapped[str | None] = mapped_column(Text)
    reply_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    ai_score_reason: Mapped[str | None] = mapped_column(Text)


class Schedule(Base):
    __tablename__ = "schedule"
    __table_args__ = (
        CheckConstraint(
            "schedule_type IN ('CALL', 'VISIT', 'MATCHING', 'CONTRACT', 'CARE_SERVICE', 'REVIEW', 'ETC')",
            name="chk_schedule_type",
        ),
        CheckConstraint(
            "schedule_status IN ('PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELED')",
            name="chk_schedule_status",
        ),
        Index("idx_schedule_care_service_id", "care_service_id"),
        Index("idx_schedule_contract_id", "contract_id"),
        Index("idx_schedule_matching_request_id", "matching_request_id"),
        Index("idx_schedule_related_person_id", "related_person_id"),
        Index("idx_schedule_start_datetime", "start_datetime"),
        Index("idx_schedule_status", "schedule_status"),
        Index("idx_schedule_type", "schedule_type"),
    )

    schedule_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(30), nullable=False)
    schedule_status: Mapped[str] = mapped_column(String(30), nullable=False)
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    related_person_id: Mapped[int | None] = mapped_column(
        ForeignKey("person.person_id", name="fk_schedule_related_person", ondelete="SET NULL", onupdate="CASCADE")
    )
    matching_request_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "matching_request.matching_request_id",
            name="fk_schedule_matching_request",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    contract_id: Mapped[int | None] = mapped_column(
        ForeignKey("contract.contract_id", name="fk_schedule_contract", ondelete="SET NULL", onupdate="CASCADE")
    )
    care_service_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "care_service.care_service_id",
            name="fk_schedule_care_service",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    memo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CallLog(Base):
    __tablename__ = "call_log"
    __table_args__ = (
        CheckConstraint(
            "call_direction IS NULL OR call_direction IN ('INBOUND', 'OUTBOUND')",
            name="chk_call_log_call_direction",
        ),
        CheckConstraint(
            "call_type IN ('MATCHING', 'CAREGIVER', 'PATIENT', 'ETC')",
            name="chk_call_log_call_type",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="chk_call_log_duration_non_negative",
        ),
        CheckConstraint(
            "recording_status IS NULL OR recording_status IN ('NOT_RECORDED', 'RECORDING', 'RECORDED', 'FAILED')",
            name="chk_call_log_recording_status",
        ),
        Index("idx_call_log_call_direction", "call_direction"),
        Index("idx_call_log_call_type", "call_type"),
        Index("idx_call_log_caller_phone", "caller_phone", postgresql_where=text("caller_phone IS NOT NULL")),
        Index("idx_call_log_created_at", "created_at"),
        Index("idx_call_log_recording_file_asset_id", "recording_file_asset_id"),
        Index("idx_call_log_recording_status", "recording_status"),
        Index("idx_call_log_related_person_id", "related_person_id"),
        Index("idx_call_log_started_at", "started_at"),
    )

    call_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    caller_name: Mapped[str | None] = mapped_column(String(100))
    caller_phone: Mapped[str | None] = mapped_column(String(30))
    related_person_id: Mapped[int | None] = mapped_column(
        ForeignKey("person.person_id", name="fk_call_log_related_person", ondelete="SET NULL", onupdate="CASCADE")
    )
    call_type: Mapped[str] = mapped_column(String(30), nullable=False)
    call_direction: Mapped[str | None] = mapped_column(String(30))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    recording_status: Mapped[str | None] = mapped_column(String(30))
    recording_file_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "file_asset.file_asset_id",
            name="fk_call_log_recording_file_asset",
            ondelete="SET NULL",
            onupdate="CASCADE",
        )
    )
    memo: Mapped[str | None] = mapped_column(Text)

    related_person: Mapped[Person | None] = relationship()
    recording_file_asset: Mapped[FileAsset | None] = relationship()
    transcript: Mapped["CallTranscript | None"] = relationship(
        back_populates="call_log",
        cascade="all, delete-orphan",
        uselist=False,
    )
    analysis: Mapped["CallAnalysis | None"] = relationship(
        back_populates="call_log",
        cascade="all, delete-orphan",
        uselist=False,
    )
    links: Mapped[list["CallLogLink"]] = relationship(
        back_populates="call_log",
        cascade="all, delete-orphan",
    )


class CallTranscript(Base):
    __tablename__ = "call_transcript"
    __table_args__ = (
        UniqueConstraint("call_log_id", name="uq_call_transcript_call_log"),
        Index("idx_call_transcript_call_log_id", "call_log_id"),
        Index("idx_call_transcript_finalized_at", "finalized_at", postgresql_where=text("finalized_at IS NOT NULL")),
    )

    call_transcript_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    call_log_id: Mapped[int] = mapped_column(
        ForeignKey(
            "call_log.call_log_id",
            name="fk_call_transcript_call_log",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transcript_text: Mapped[str | None] = mapped_column(Text)

    call_log: Mapped[CallLog] = relationship(back_populates="transcript")


class CallAnalysis(Base):
    __tablename__ = "call_analysis"
    __table_args__ = (
        UniqueConstraint("call_log_id", name="uq_call_analysis_call_log"),
        CheckConstraint(
            "analysis_status IN ('NOT_STARTED', 'PROCESSING', 'SUCCESS', 'FAILED', 'MANUAL_REQUIRED')",
            name="chk_call_analysis_status",
        ),
        Index("idx_call_analysis_call_log_id", "call_log_id"),
        Index("idx_call_analysis_finalized_at", "finalized_at", postgresql_where=text("finalized_at IS NOT NULL")),
        Index("idx_call_analysis_status", "analysis_status"),
    )

    call_analysis_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    call_log_id: Mapped[int] = mapped_column(
        ForeignKey(
            "call_log.call_log_id",
            name="fk_call_analysis_call_log",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    analysis_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="NOT_STARTED",
        server_default=text("'NOT_STARTED'"),
    )
    summary: Mapped[str | None] = mapped_column(Text)
    analysis_result_json: Mapped[dict | None] = mapped_column(JSONB)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    call_log: Mapped[CallLog] = relationship(back_populates="analysis")


class CallLogLink(Base):
    __tablename__ = "call_log_link"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(matching_request_id, temporary_assignment_id, contract_id, care_service_id) = 1",
            name="chk_call_log_link_one_target",
        ),
        Index("idx_call_log_link_call_log_id", "call_log_id"),
        Index(
            "idx_call_log_link_matching_request_id",
            "matching_request_id",
            postgresql_where=text("matching_request_id IS NOT NULL"),
        ),
        Index(
            "idx_call_log_link_temporary_assignment_id",
            "temporary_assignment_id",
            postgresql_where=text("temporary_assignment_id IS NOT NULL"),
        ),
        Index(
            "idx_call_log_link_contract_id",
            "contract_id",
            postgresql_where=text("contract_id IS NOT NULL"),
        ),
        Index(
            "idx_call_log_link_care_service_id",
            "care_service_id",
            postgresql_where=text("care_service_id IS NOT NULL"),
        ),
    )

    call_log_link_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    call_log_id: Mapped[int] = mapped_column(
        ForeignKey(
            "call_log.call_log_id",
            name="fk_call_log_link_call_log",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    matching_request_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "matching_request.matching_request_id",
            name="fk_call_log_link_matching_request",
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    temporary_assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "temporary_assignment.temporary_assignment_id",
            name="fk_call_log_link_temporary_assignment",
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    contract_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "contract.contract_id",
            name="fk_call_log_link_contract",
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    care_service_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "care_service.care_service_id",
            name="fk_call_log_link_care_service",
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    memo: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    call_log: Mapped[CallLog] = relationship(back_populates="links")
    matching_request: Mapped[MatchingRequest | None] = relationship()
    temporary_assignment: Mapped[TemporaryAssignment | None] = relationship()
    contract: Mapped[Contract | None] = relationship()
    care_service: Mapped[CareService | None] = relationship()


# Backward-compatible import aliases while repository/API code migrates to call_log naming.
CallRecord = CallLog
CallRecordLink = CallLogLink


class ChatbotConversation(Base):
    __tablename__ = "chatbot_conversation"

    chatbot_conversation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    page_context: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now() + '7 days'::interval"),
    )

    messages: Mapped[list["ChatbotMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class ChatbotMessage(Base):
    __tablename__ = "chatbot_message"
    __table_args__ = (
        CheckConstraint("sender_type IN ('USER', 'ASSISTANT')", name="chk_chatbot_message_sender_type"),
        Index("idx_chatbot_message_conversation_id", "chatbot_conversation_id"),
        Index("idx_chatbot_message_created_at", "created_at"),
    )

    chatbot_message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chatbot_conversation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "chatbot_conversation.chatbot_conversation_id",
            name="fk_chatbot_message_conversation",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    conversation: Mapped[ChatbotConversation] = relationship(back_populates="messages")


class OperationQALog(Base):
    __tablename__ = "operation_qa_log"
    __table_args__ = (
        CheckConstraint(
            "answer_status IN ('SUCCESS', 'FAILED', 'FALLBACK')",
            name="chk_operation_qa_log_answer_status",
        ),
        Index("idx_operation_qa_log_created_at", "created_at"),
        Index("idx_operation_qa_log_route_intent", "route", "intent"),
    )

    operation_qa_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    route: Mapped[str | None] = mapped_column(String(30))
    intent: Mapped[str | None] = mapped_column(String(60))
    answer_status: Mapped[str] = mapped_column(String(30), nullable=False, default="SUCCESS", server_default=text("'SUCCESS'"))
    error_message: Mapped[str | None] = mapped_column(Text)
    used_tools: Mapped[dict | None] = mapped_column(JSONB)
    source_json: Mapped[dict | None] = mapped_column(JSONB)
    warning_json: Mapped[dict | None] = mapped_column(JSONB)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    feedback_score: Mapped[int | None] = mapped_column(Integer)
    feedback_comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
