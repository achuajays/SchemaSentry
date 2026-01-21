"""
Sample Patient API - A mock healthcare API for testing SchemaSentry.

This API intentionally has some "drifts" from its OpenAPI spec:
- The `coverage_status` field is sometimes missing in eligibility responses
- The `insurance` field is sometimes null even for patients who have insurance
- An undocumented `internal_score` field sometimes appears

Run this on a different port (e.g., 8001) alongside SchemaSentry.
Usage: python sample_api.py
"""

import random
import uuid
from datetime import datetime, date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn


# --- Models ---

class Insurance(BaseModel):
    provider: str
    policy_number: str
    group_number: Optional[str] = None


class Patient(BaseModel):
    id: str
    name: str
    date_of_birth: str
    email: Optional[str] = None
    phone: Optional[str] = None
    insurance: Optional[Insurance] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class PatientCreate(BaseModel):
    name: str
    date_of_birth: str
    email: Optional[str] = None
    phone: Optional[str] = None
    insurance_id: Optional[str] = None


class CoverageDetails(BaseModel):
    deductible: float
    copay: float
    coinsurance: Optional[float] = None


class EligibilityResponse(BaseModel):
    patient_id: str
    eligible: bool
    coverage_status: Optional[str] = None  # Sometimes missing intentionally!
    coverage_details: Optional[CoverageDetails] = None
    checked_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    # Undocumented field - will trigger "undocumented field" detection
    internal_score: Optional[float] = None


# --- Sample Data ---

PATIENTS_DB: dict[str, Patient] = {
    "pat-001": Patient(
        id="pat-001",
        name="John Doe",
        date_of_birth="1985-03-15",
        email="john.doe@email.com",
        phone="555-123-4567",
        insurance=Insurance(
            provider="BlueCross",
            policy_number="BC123456",
            group_number="GRP789"
        ),
        created_at="2024-01-15T10:30:00Z"
    ),
    "pat-002": Patient(
        id="pat-002",
        name="Jane Smith",
        date_of_birth="1990-07-22",
        email="jane.smith@email.com",
        insurance=None,  # No insurance
        created_at="2024-01-18T14:00:00Z"
    ),
    "pat-003": Patient(
        id="pat-003",
        name="Bob Johnson",
        date_of_birth="1978-11-30",
        phone="555-987-6543",
        insurance=Insurance(
            provider="Aetna",
            policy_number="AET999888"
        ),
        created_at="2024-01-20T09:15:00Z"
    ),
}


# --- FastAPI App ---

app = FastAPI(
    title="Patient API",
    description="Sample healthcare API for testing SchemaSentry contract monitoring.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Traffic Logging Middleware ---

@app.middleware("http")
async def log_traffic(request, call_next):
    """Log all traffic for SchemaSentry observation."""
    import json
    
    response = await call_next(request)
    
    # Log to console (you could also send this to SchemaSentry)
    print(f"[TRAFFIC] {request.method} {request.url.path} -> {response.status_code}")
    
    return response


# --- Endpoints ---

@app.get("/")
async def root():
    return {
        "message": "Patient API - Sample API for SchemaSentry testing",
        "version": "1.0.0",
        "endpoints": ["/patients", "/patients/{id}", "/eligibility"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/patients", response_model=list[Patient])
async def list_patients():
    """List all patients."""
    patients = list(PATIENTS_DB.values())
    
    # INTENTIONAL DRIFT: Sometimes omit insurance even when it exists (30% of the time)
    # This simulates real-world API inconsistencies
    if random.random() < 0.3:
        patients = [
            Patient(**{**p.model_dump(), "insurance": None})
            for p in patients
        ]
    
    return patients


@app.post("/patients", response_model=Patient, status_code=201)
async def create_patient(patient: PatientCreate):
    """Create a new patient."""
    patient_id = f"pat-{str(uuid.uuid4())[:8]}"
    
    new_patient = Patient(
        id=patient_id,
        name=patient.name,
        date_of_birth=patient.date_of_birth,
        email=patient.email,
        phone=patient.phone,
        insurance=None,  # Would need to look up insurance_id
    )
    
    PATIENTS_DB[patient_id] = new_patient
    return new_patient


@app.get("/patients/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str):
    """Get a patient by ID."""
    if patient_id not in PATIENTS_DB:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return PATIENTS_DB[patient_id]


@app.get("/eligibility", response_model=EligibilityResponse)
async def check_eligibility(patient_id: str = Query(..., description="Patient ID")):
    """
    Check patient eligibility.
    
    NOTE: This endpoint has INTENTIONAL DRIFTS from the OpenAPI spec:
    - coverage_status is sometimes missing (violates 'required')
    - internal_score is sometimes included (undocumented field)
    """
    if patient_id not in PATIENTS_DB:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient = PATIENTS_DB[patient_id]
    has_insurance = patient.insurance is not None
    
    # INTENTIONAL DRIFT #1: Sometimes omit coverage_status (40% of the time)
    # This is a BREAKING CHANGE - the spec says it's required!
    include_coverage_status = random.random() > 0.4
    
    # INTENTIONAL DRIFT #2: Sometimes include undocumented field (50% of the time)
    include_internal_score = random.random() > 0.5
    
    response = EligibilityResponse(
        patient_id=patient_id,
        eligible=has_insurance,
        coverage_status="active" if has_insurance and include_coverage_status else None,
        coverage_details=CoverageDetails(
            deductible=500.0,
            copay=25.0,
            coinsurance=0.2
        ) if has_insurance else None,
        internal_score=random.uniform(0.5, 1.0) if include_internal_score else None,
    )
    
    # Remove None coverage_status entirely (not just set to None) to simulate missing field
    if not include_coverage_status:
        response_dict = response.model_dump()
        del response_dict["coverage_status"]
        return response_dict
    
    return response


# --- Run ---

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🏥 Sample Patient API - For SchemaSentry Testing            ║
║                                                               ║
║   This API has INTENTIONAL contract drifts:                   ║
║   • coverage_status sometimes missing (breaking!)             ║
║   • insurance sometimes null unexpectedly                     ║
║   • internal_score (undocumented field) sometimes appears     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    print("🚀 Starting Sample Patient API at http://localhost:8001")
    print("📖 API docs at http://localhost:8001/docs")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
