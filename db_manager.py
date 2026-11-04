"""Esquema, seed de demostración y utilidades internas. Autorización en security.py.
No ofrece CRUD, autenticación ni borrado de bases sin controles.
"""
import os,io,sqlite3,datetime as dt
import secrets
import json
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import bcrypt,pyotp,qrcode
import qrcode.image.pil

DB_PATH = os.getenv("ST_DB_PATH", "security_team.db")

# Emisor mostrado en la app de autenticación (Google Authenticator, Authy...).
ISSUER_NAME = "SECURITY TEAM - UPY"

# Contraseña temporal robusta entregada por el Admin (se cambia al gusto).
TEMP_PASSWORD = "SoloPruebasLocal2026!" if os.environ.get("ST_TEST_MODE") == "1" else secrets.token_urlsafe(32)

# Política anti-fuerza bruta.
MAX_FAILED_ATTEMPTS = 3

# --- Roles RBAC -------------------------------------------------------------
ROLE_SYSTEM_ADMIN = "system_admin"  # Propietario / administrador del sistema
ROLE_DPO = "dpo"                 # Responsable de protección de datos
ROLE_AREA_ADMIN = "area_admin"   # Administrador de Área (alcance limitado)
ROLE_USER = "user"               # Usuario final
GLOBAL_ROLES = (ROLE_SYSTEM_ADMIN, ROLE_DPO)

# --- Áreas operativas -------------------------------------------------------
AREA_AC = "Access Control"
AREA_MON = "Monitoring"
AREA_IM = "Identity Management"
AREA_IAM = "Identity and Access Management"
AREA_WILDCARD = "Comodines"

AREAS = [AREA_AC, AREA_MON, AREA_IM, AREA_IAM, AREA_WILDCARD]

ROLE_LABELS = {
    ROLE_SYSTEM_ADMIN: "Administrador del sistema",
    ROLE_DPO: "DPO",
    ROLE_AREA_ADMIN: "Area Admin",
    ROLE_USER: "User",
}


# ----------------------------------------------------------------------------
# SEED: 33 IDENTIDADES FICTICIAS PARA PRUEBAS Y DEMO
# Formato de tupla: (username, nombre_completo, rol, area, es_guard)
# ----------------------------------------------------------------------------
SEED_USERS = [
    # ----------------------------- DPO (1) --------------------------------
    ("9900001", "PERSONA DE EJEMPLO 01", ROLE_DPO, None, 0),

    # ------------------------ Líderes de Área (4) -------------------------
    ("9900002", "PERSONA DE EJEMPLO 02", ROLE_AREA_ADMIN, AREA_AC, 0),
    ("9900003", "PERSONA DE EJEMPLO 03", ROLE_AREA_ADMIN, AREA_MON, 0),
    ("9900004", "PERSONA DE EJEMPLO 04", ROLE_AREA_ADMIN, AREA_IM, 0),
    ("9900005", "PERSONA DE EJEMPLO 05", ROLE_AREA_ADMIN, AREA_IAM, 0),

    # --------------------------- Access Control (6) -----------------------
    ("9900006", "PERSONA DE EJEMPLO 06", ROLE_USER, AREA_AC, 1),   # Guard
    ("9900007", "PERSONA DE EJEMPLO 07", ROLE_USER, AREA_AC, 0),
    ("9900008", "PERSONA DE EJEMPLO 08", ROLE_USER, AREA_AC, 0),
    ("9900009", "PERSONA DE EJEMPLO 09", ROLE_USER, AREA_AC, 0),
    ("9900010", "PERSONA DE EJEMPLO 10", ROLE_USER, AREA_AC, 0),
    ("9900011", "PERSONA DE EJEMPLO 11", ROLE_USER, AREA_AC, 0),

    # ----------------------------- Monitoring (6) -------------------------
    ("9900012", "PERSONA DE EJEMPLO 12", ROLE_USER, AREA_MON, 0),
    ("9900013", "PERSONA DE EJEMPLO 13", ROLE_USER, AREA_MON, 0),
    ("9900014", "PERSONA DE EJEMPLO 14", ROLE_USER, AREA_MON, 0),
    ("9900015", "PERSONA DE EJEMPLO 15", ROLE_USER, AREA_MON, 0),
    ("9900016", "PERSONA DE EJEMPLO 16", ROLE_USER, AREA_MON, 1),  # Guard
    ("9900017", "PERSONA DE EJEMPLO 17", ROLE_USER, AREA_MON, 0),

    # ------------------------ Identity Management (6) ---------------------
    ("9900018", "PERSONA DE EJEMPLO 18", ROLE_USER, AREA_IM, 0),
    ("9900019", "PERSONA DE EJEMPLO 19", ROLE_USER, AREA_IM, 0),
    ("9900020", "PERSONA DE EJEMPLO 20", ROLE_USER, AREA_IM, 0),
    ("9900021", "PERSONA DE EJEMPLO 21", ROLE_USER, AREA_IM, 0),
    ("9900022", "PERSONA DE EJEMPLO 22", ROLE_USER, AREA_IM, 0),
    ("9900023", "PERSONA DE EJEMPLO 23", ROLE_USER, AREA_IM, 0),

    # ------------------- Identity and Access Management (7) ---------------
    ("9900024", "PERSONA DE EJEMPLO 24", ROLE_USER, AREA_IAM, 0),
    ("9900025", "PERSONA DE EJEMPLO 25", ROLE_USER, AREA_IAM, 0),
    ("9900026", "PERSONA DE EJEMPLO 26", ROLE_USER, AREA_IAM, 0),
    ("9900027", "PERSONA DE EJEMPLO 27", ROLE_USER, AREA_IAM, 0),
    ("9900028", "PERSONA DE EJEMPLO 28", ROLE_USER, AREA_IAM, 0),
    ("9900029", "PERSONA DE EJEMPLO 29", ROLE_USER, AREA_IAM, 0),
    ("9900030", "PERSONA DE EJEMPLO 30", ROLE_USER, AREA_IAM, 1),  # Guard

    # ------------------------------ Comodines (3) -------------------------
    ("9900031", "PERSONA DE EJEMPLO 31", ROLE_USER, AREA_WILDCARD, 0),
    ("9900032", "PERSONA DE EJEMPLO 32", ROLE_USER, AREA_WILDCARD, 0),
    ("9900033", "PERSONA DE EJEMPLO 33", ROLE_USER, AREA_WILDCARD, 0),
]


# ----------------------------------------------------------------------------
# UTILIDADES INTERNAS
# ----------------------------------------------------------------------------
def _now() -> str:
    """Devuelve la estampa de tiempo actual en ISO-8601 (segundos)."""
    return dt.datetime.now().isoformat(timespec="seconds")


def _today_prefix() -> str:
    """Prefijo YYYY-MM-DD para filtrar eventos del día actual."""
    return dt.date.today().isoformat()


@contextmanager
def get_connection(timeout=15):
    """
    Context manager de conexión a SQLite.

    - Se habilita `row_factory = Row` para acceso a columnas por nombre.
    - Commit automático si no hay excepción; rollback en caso de error.
    """
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(plain_password: str) -> str:
    """Genera un hash bcrypt con salt aleatorio (costo por defecto = 12)."""
    pwd_bytes = plain_password.encode("utf-8")
    if not 10 <= len(plain_password) or len(pwd_bytes)>72:
        raise ValueError("Contraseña fuera de los límites permitidos.")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def generate_mfa_secret() -> str:
    """Genera un secreto TOTP Base32 nuevo (nunca se genera por el Admin)."""
    return pyotp.random_base32()


def build_provisioning_uri(secret: str, username: str) -> str:
    """Construye el otpauth:// URI que consumen las apps autenticadoras."""
    return pyotp.TOTP(secret).provisioning_uri(
        name=username, issuer_name=ISSUER_NAME
    )


def generate_qr_png(uri: str) -> bytes:
    """
    Genera el Código QR como bytes PNG (listo para `st.image`).
    El QR NUNCA se persiste en disco ni en la base de datos.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0B1F3A", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def write_audit(conn, actor, action, details="", target=""):
    """
    Inserta un evento de auditoría usando la conexión provista (parametrizado).
    Se expone una variante pública `log_event` para uso puntual.
    """
    conn.execute(
        """
        INSERT INTO audit_log (timestamp, actor, action, target, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (_now(), actor or "sistema", action, target or "", details or ""),
    )


def log_event(actor, action, details="", target=""):
    """Registra un evento de auditoría abriendo su propia conexión."""
    with get_connection() as conn:
        write_audit(conn, actor, action, details, target)


def init_db():
    """
    Crea las tablas, índices y TRIGGERS de inmutabilidad.
    Idempotente: puede ejecutarse en cada arranque sin riesgo.
    """
    with get_connection() as conn:
        # ------------------------------ USUARIOS ------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                username         TEXT    NOT NULL UNIQUE,        -- matrícula
                full_name        TEXT    NOT NULL,
                role             TEXT    NOT NULL DEFAULT 'user',
                area             TEXT,                           -- NULL para DPO
                is_guard         INTEGER NOT NULL DEFAULT 0,     -- rol secundario
                password_hash    TEXT    NOT NULL,               -- bcrypt
                mfa_secret       TEXT,                           -- NULL hasta enrolar
                mfa_configured   INTEGER NOT NULL DEFAULT 0,     -- 0 = pendiente
                rfid_uid         TEXT    UNIQUE,                 -- NULL permitido
                failed_attempts  INTEGER NOT NULL DEFAULT 0,
                is_locked        INTEGER NOT NULL DEFAULT 0,
                is_active        INTEGER NOT NULL DEFAULT 1,     -- soft-delete
                created_at       TEXT    NOT NULL,
                updated_at       TEXT,
                last_login       TEXT
            )
            """
        )

        # ------------------------------ AUDITORÍA -----------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                actor     TEXT,
                action    TEXT NOT NULL,
                target    TEXT,
                details   TEXT
            )
            """
        )

        # Índices de rendimiento para consultas frecuentes.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_area ON users(area)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp)"
        )

        # ------------- TRIGGERS: BITÁCORA INMUTABLE (solo INSERT) ------------
        conn.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS trg_audit_no_update
            BEFORE UPDATE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log es inmutable: UPDATE prohibido');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_audit_no_delete
            BEFORE DELETE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log es inmutable: DELETE prohibido');
            END;
            """
        )


def seed_users():
    """Carga opcional de ejemplos; nunca incorpora personas reales."""
    if os.environ.get("ST_TEST_MODE") != "1" and os.environ.get("ST_DEMO_SEED") != "1":
        return 0
    # El primer arranque calcula 33 hashes bcrypt; otro arranque espera esa
    # carga completa sin fallar al superar el timeout ordinario de escrituras.
    with get_connection(timeout=120) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        if conn.execute("SELECT 1 FROM app_meta WHERE key='demo_seed_v1'").fetchone():return 0
        if conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
            conn.execute("INSERT INTO app_meta VALUES('demo_seed_v1',?)",(_now(),))
            return 0
        for username,name,role,area,guard in SEED_USERS:
            conn.execute("INSERT INTO users(username,full_name,role,area,is_guard,password_hash,created_at) VALUES(?,?,?,?,?,?,?)",
                         (username,name,role,area,guard,hash_password(TEMP_PASSWORD),_now()))
        conn.execute("INSERT INTO app_meta VALUES('demo_seed_v1',?)",(_now(),))
        write_audit(conn,'sistema','SEED_USERS',f'{len(SEED_USERS)} cuentas demo')
        return len(SEED_USERS)


# Migraciones aditivas v1.3.0
from terms_policy import VERSION as POLICY_VERSION
TERMS_VERSION = os.getenv("TERMS_VERSION", POLICY_VERSION)

# Roles (respetar la separación de privilegios existente).
ROLE_SYSTEM_ADMIN = "system_admin"
ROLE_DPO = "dpo"
ROLE_AREA_ADMIN = "area_admin"
ROLE_USER = "user"

# Zonas físicas soportadas.
ZONE_VAULT = "DATA_CENTER_VAULT"
ZONE_SERVER = "SERVER_ROOM"
ZONE_CCTV = "MONITORING_CCTV"
ZONE_GENERAL = "GENERAL_ACCESS"

ZONES = {
    ZONE_VAULT: "Bóveda Principal Data Center",
    ZONE_SERVER: "Sala de Servidores Críticos",
    ZONE_CCTV: "Centro de Monitoreo CCTV",
    ZONE_GENERAL: "Acceso General",
}

# Zona por defecto según el área operativa.
_AREA_DEFAULT_ZONE = {
    "Access Control": ZONE_VAULT,
    "Monitoring": ZONE_CCTV,
    "Identity Management": ZONE_SERVER,
    "Identity and Access Management": ZONE_GENERAL,
    "Comodines": ZONE_GENERAL,
}

# Catálogo inicial de licencias académicas simuladas.
LICENSE_SEED = [
    ("LIC-DC-VAULT", "Data Center Physical & RFID Clearance", 5),
    ("LIC-SRV-CRIT", "Critical Server Administration Suite", 10),
    ("LIC-CCTV-MON", "CCTV Monitoring & IP Camera Suite", 10),
    ("LIC-CCTV-ADMIN", "Administración de cámaras (permiso interno)", 40),
    ("LIC-IAM-STD", "Enterprise Identity & QR Standard Access", 40),
]

VISITOR_LIMIT_TOKENS = {  # duración -> timedelta
    "2h": timedelta(hours=2), "4h": timedelta(hours=4),
    "8h": timedelta(hours=8), "24h": timedelta(hours=24),
}


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ----------------------------------------------------------------------------
# UTILIDADES DE MIGRACIÓN
# ----------------------------------------------------------------------------
def _columnas(conn, tabla):
    """Devuelve el conjunto de columnas existentes de una tabla (seguro)."""
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({tabla})").fetchall()}
    except sqlite3.Error:
        return set()


def _add_column(conn, tabla, columna, ddl):
    """Añade una columna SOLO si no existe (migración aditiva segura)."""
    if columna not in _columnas(conn, tabla):
        conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {ddl}")


def _user_col(conn, *candidatos, default=None):
    """Devuelve el primer nombre de columna existente en `users` (o default)."""
    cols = _columnas(conn, "users")
    for c in candidatos:
        if c in cols:
            return c
    return default


def apply_v130_migrations(conn):
    """
    Aplica TODAS las migraciones de la v1.3.0. Idempotente.
    Llamar durante el arranque de la BD (junto a las migraciones ya existentes).
    NO recrea ni borra datos.
    """
    # ---- 1) Nuevas columnas en users ------------------------------------
    _add_column(conn, "users", "terms_accepted", "INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "users", "terms_accepted_at", "TEXT")
    _add_column(conn, "users", "terms_version", "TEXT")
    _add_column(conn, "users", "allowed_zones", "TEXT")  # JSON lista

    # ---- 2) Tabla access_events (bitácora de la Terminal de Acceso) -----
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS access_events (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_type     TEXT NOT NULL,          -- USER | VISITOR
            subject_id       TEXT NOT NULL,          -- matrícula o visitor_id
            subject_name     TEXT,
            role_or_type     TEXT,
            zone             TEXT,
            method           TEXT,                   -- RFID_125KHZ | QR_BADGE
            direction        TEXT,                   -- CHECK_IN | CHECK_OUT
            verdict          TEXT NOT NULL,          -- VERIFIED | DENIED
            reason           TEXT,
            operator_matricula TEXT,
            created_at       TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_access_created ON access_events(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_access_subject ON access_events(subject_id)")

    # ---- 3) Tabla visitors ----------------------------------------------
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visitors (
            visitor_id       TEXT PRIMARY KEY,       -- VIS-XXXX
            full_name        TEXT NOT NULL,
            organization     TEXT,
            visit_reason     TEXT,
            host_matricula   TEXT,
            allowed_zone     TEXT,
            valid_until      TEXT,
            terms_accepted   INTEGER NOT NULL DEFAULT 0,
            terms_accepted_at TEXT,
            status           TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE|REVOKED|EXPIRED
            qr_token_hash    TEXT,
            created_at       TEXT NOT NULL
        )
        """
    )

    _add_column(conn, "visitors", "terms_version", "TEXT")

    # ---- 4) Catálogo y asignación de licencias --------------------------
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS licenses_catalog (
            license_id   TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            seats        INTEGER NOT NULL,
            created_at   TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_licenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula   TEXT NOT NULL,
            license_id  TEXT NOT NULL,
            assigned_by TEXT,
            assigned_at TEXT NOT NULL,
            UNIQUE(matricula, license_id)
        )
        """
    )
    for lic_id, name, seats in LICENSE_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO licenses_catalog (license_id, name, seats, created_at) "
            "VALUES (?, ?, ?, ?)",
            (lic_id, name, seats, _now_iso()),
        )

    # ---- 5) Triggers de inmutabilidad para access_events (append-only) --
    for name, operation in [('update','UPDATE'),('delete','DELETE')]:
        conn.execute(f"CREATE TRIGGER IF NOT EXISTS trg_access_no_{name} BEFORE {operation} ON access_events BEGIN SELECT RAISE(ABORT,'access_events inmutable'); END")
    conn.execute("CREATE TRIGGER IF NOT EXISTS trg_access_no_replace BEFORE INSERT ON access_events WHEN EXISTS(SELECT 1 FROM access_events WHERE id=NEW.id) BEGIN SELECT RAISE(ABORT,'access_events inmutable'); END")

    # ---- 6) Backfill de allowed_zones para usuarios existentes ----------
    rows = conn.execute(
        "SELECT username AS matricula, role, area, " +
        f"{_user_col(conn, 'is_guard', default='0') or '0'} AS is_guard, allowed_zones "
        "FROM users WHERE allowed_zones IS NULL OR allowed_zones = ''"
    ).fetchall()
    for r in rows:
        zonas = default_zones(dict(r).get("role"), dict(r).get("area"),
                              bool(dict(r).get("is_guard")))
        conn.execute("UPDATE users SET allowed_zones = ? WHERE username = ?",
                     (json.dumps(zonas), dict(r)["matricula"]))
    return True


def default_zones(role, area, is_guard=False):
    """Zonas por defecto coherentes con el rol y el área."""
    if role in (ROLE_SYSTEM_ADMIN, ROLE_DPO):
        return [ZONE_VAULT, ZONE_SERVER, ZONE_CCTV, ZONE_GENERAL]
    zonas = {ZONE_GENERAL}
    if is_guard:
        zonas.add(ZONE_CCTV)
    if role == ROLE_AREA_ADMIN:
        z = _AREA_DEFAULT_ZONE.get(area)
        if z:
            zonas.add(z)
    elif area in _AREA_DEFAULT_ZONE:
        zonas.add(_AREA_DEFAULT_ZONE[area])
    # Mantener orden estable según ZONES.
    return [z for z in ZONES if z in zonas]



def migrate_extensions():
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        apply_v130_migrations(conn)
        _add_column(conn,'users','rfid_aliases',"TEXT NOT NULL DEFAULT '[]'")
        conn.execute("CREATE TRIGGER IF NOT EXISTS rfid_revoke_aliases AFTER UPDATE OF rfid_uid,is_active ON users WHEN NEW.rfid_uid IS NOT OLD.rfid_uid OR NEW.is_active=0 BEGIN UPDATE users SET rfid_aliases='[]' WHERE id=NEW.id; END")
        _add_column(conn,'access_events','subject_area','TEXT')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_access_presence ON access_events(subject_type,subject_id,zone,verdict,id)')
        conn.execute("CREATE TABLE IF NOT EXISTS mobile_passes(token_hash TEXT PRIMARY KEY,subject_type TEXT,subject_id TEXT,security_version INTEGER,expires_at REAL,created_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS camera_channels(id INTEGER PRIMARY KEY,name TEXT NOT NULL,url TEXT NOT NULL,updated_at TEXT)")
        _add_column(conn,'camera_channels','profile',"TEXT NOT NULL DEFAULT 'balanced'")
        conn.execute("CREATE TABLE IF NOT EXISTS access_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        conn.execute("INSERT OR IGNORE INTO access_settings VALUES('rfid_capacity','5')")
        conn.execute("CREATE TRIGGER IF NOT EXISTS offboard_licenses AFTER UPDATE OF is_active ON users WHEN NEW.is_active=0 BEGIN INSERT INTO audit_log(timestamp,actor,action,target,details) SELECT datetime('now'),'sistema','LICENSE_REVOKED',OLD.username,license_id||' por baja' FROM user_licenses WHERE matricula=OLD.username; DELETE FROM user_licenses WHERE matricula=OLD.username; END")
        conn.execute("CREATE TRIGGER IF NOT EXISTS rename_licenses AFTER UPDATE OF username ON users WHEN NEW.username<>OLD.username BEGIN UPDATE user_licenses SET matricula=NEW.username WHERE matricula=OLD.username; END")
