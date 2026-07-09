"""Shared paths, constants, and reference data for the ETL pipeline."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_SYNTHETIC = REPO_ROOT / "data" / "synthetic"
MODELS_DIR = REPO_ROOT / "models"

SEED = 42

# Neighbourhoods matching the style of the Kaggle Medical Appointment No Shows
# dataset (Vitoria, Brazil). Weights approximate the skewed distribution seen
# in the original data.
NEIGHBOURHOODS = [
    ("JARDIM CAMBURI", 0.070), ("MARIA ORTIZ", 0.052), ("RESISTENCIA", 0.040),
    ("JARDIM DA PENHA", 0.035), ("ITARARE", 0.032), ("CENTRO", 0.030),
    ("TABUAZEIRO", 0.028), ("SANTA MARTHA", 0.027), ("JESUS DE NAZARETH", 0.025),
    ("BONFIM", 0.024), ("SANTO ANTONIO", 0.024), ("SAO PEDRO", 0.023),
    ("CARATOIRA", 0.023), ("JABOUR", 0.022), ("ANDORINHAS", 0.022),
    ("ILHA DO PRINCIPE", 0.021), ("SAO JOSE", 0.021), ("ROMAO", 0.020),
    ("GURIGICA", 0.020), ("MARUIPE", 0.020), ("DA PENHA", 0.019),
    ("SAO CRISTOVAO", 0.019), ("REDENCAO", 0.018), ("SANTOS DUMONT", 0.018),
    ("FORTE SAO JOAO", 0.018), ("BELA VISTA", 0.017), ("JOANA DARC", 0.017),
    ("CRUZAMENTO", 0.016), ("INHANGUETA", 0.016), ("VILA RUBIM", 0.015),
    ("PRAIA DO SUA", 0.015), ("SANTA CECILIA", 0.014), ("BENTO FERREIRA", 0.014),
    ("SOLON BORGES", 0.013), ("SANTA LUIZA", 0.012), ("BARRO VERMELHO", 0.012),
    ("MONTE BELO", 0.012), ("PARQUE MOSCOSO", 0.011), ("GOIABEIRAS", 0.011),
    ("PRAIA DO CANTO", 0.010),
]

CLINICS = [
    # clinic_id, clinic_name, location, service_line, target_utilization
    (1, "Downtown Family Medicine", "Centro", "Primary Care", 0.85),
    (2, "Northside Community Health Center", "Maria Ortiz", "Primary Care", 0.82),
    (3, "Harbor Internal Medicine & Cardiology", "Jardim Camburi", "Specialty Care", 0.80),
    (4, "Eastside Pediatrics & Family Care", "Jardim da Penha", "Pediatrics", 0.85),
    (5, "Riverside Women's Health Center", "Praia do Canto", "Women's Health", 0.80),
    (6, "Lakeview Behavioral Health & Dermatology", "Maruipe", "Specialty Care", 0.78),
]

SPECIALTIES_BY_CLINIC = {
    1: ["Family Medicine", "Internal Medicine"],
    2: ["Family Medicine", "Internal Medicine"],
    3: ["Internal Medicine", "Cardiology", "Endocrinology"],
    4: ["Pediatrics", "Family Medicine"],
    5: ["Obstetrics & Gynecology", "Family Medicine"],
    6: ["Behavioral Health", "Dermatology"],
}

PROVIDER_FIRST = [
    "Ana", "Carlos", "Elena", "Marcus", "Priya", "Daniel", "Sofia", "James",
    "Leila", "Rafael", "Nina", "Omar", "Grace", "Victor", "Camila", "Andre",
    "Renata", "Lucas", "Beatriz", "Felipe", "Isabel", "Thiago", "Marina",
    "Paulo", "Alice", "Bruno", "Clara", "Diego", "Helena", "Gustavo",
    "Julia", "Mateus", "Larissa", "Ricardo", "Vanessa", "Eduardo",
]

PROVIDER_LAST = [
    "Silva", "Mendes", "Rocha", "Almeida", "Iyer", "Costa", "Martins",
    "Whitfield", "Hassan", "Oliveira", "Petrov", "Farouk", "Nakamura",
    "Moreira", "Duarte", "Barbosa", "Freitas", "Cardoso", "Lima", "Souza",
    "Teixeira", "Ribeiro", "Carvalho", "Gomes", "Pereira", "Fernandes",
    "Vieira", "Lopes", "Monteiro", "Araujo", "Batista", "Correia",
    "Nogueira", "Pinto", "Ramos", "Tavares",
]

APPOINTMENT_TYPES = ["Follow-up", "New Patient", "Annual Physical", "Procedure", "Telehealth"]
APPOINTMENT_TYPE_WEIGHTS = [0.42, 0.22, 0.16, 0.12, 0.08]

STAFF_USERS = [
    # staff_id, staff_name, role
    (1, "Monica Reyes", "Patient Access Coordinator"),
    (2, "Jordan Blake", "Patient Access Coordinator"),
    (3, "Aisha Thompson", "Scheduling Specialist"),
    (4, "Kevin O'Neal", "Scheduling Specialist"),
    (5, "Sandra Kim", "Patient Access Manager"),
    (6, "Luis Herrera", "Outreach Specialist"),
]


def ensure_dirs() -> None:
    for d in (DATA_RAW, DATA_PROCESSED, DATA_SYNTHETIC, MODELS_DIR):
        d.mkdir(parents=True, exist_ok=True)
