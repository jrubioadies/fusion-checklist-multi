"""
profiles.py — Perfiles de cliente: instancias Oracle Fusion a comparar + usuarios.

Cada cliente vive en ~/.config/fusion-checklist/clients/<slug>.json:

    {
      "name": "Cliente X",
      "environments": [
        {"name": "PROD", "base": "https://xxx.fa.em2.oraclecloud.com", "user": "jdoe", "compare": true},
        {"name": "TEST", "base": "https://xxx-test.fa.em2.oraclecloud.com", "user": "jdoe", "compare": true}
      ],
      "sql_report": "/Custom/SQLTools/SQLConReport.xdo",
      "fbdi_source": "PROD", "fbdi_target": "TEST"
    }

Las contraseñas NO se guardan en el JSON: van al llavero del sistema
(Keychain / Credential Manager / Secret Service) vía `keyring`, con
servicio "fusion-checklist" y cuenta "<slug>/<entorno>". Si `keyring` no
está disponible las contraseñas solo viven en memoria durante la sesión.
"""
import json, os, re, time, unicodedata
from pathlib import Path
from urllib.parse import urlparse

from fusion_client import bip as fbip

CLIENTS_DIR = Path.home() / ".config" / "fusion-checklist" / "clients"
KEYRING_SERVICE = "fusion-checklist"

try:
    import keyring as _keyring
    _keyring.get_keyring()
except Exception:  # paquete ausente o sin backend en este SO
    _keyring = None


def keyring_available():
    return _keyring is not None


def slugify(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "cliente"


def _path(slug):
    return CLIENTS_DIR / f"{slugify(slug)}.json"


def list_clients():
    if not CLIENTS_DIR.exists():
        return []
    out = []
    for p in sorted(CLIENTS_DIR.glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        out.append({"slug": p.stem, "name": d.get("name") or p.stem,
                    "environments": [e.get("name") for e in d.get("environments") or []]})
    return out


def load(slug):
    p = _path(slug)
    return json.loads(p.read_text()) if p.exists() else None


def save(profile, passwords=None):
    """Guarda el perfil (sin contraseñas) y las contraseñas en el llavero.
    passwords: {env_name: password}. Devuelve el slug."""
    slug = slugify(profile.get("slug") or profile.get("name"))
    clean = {k: v for k, v in profile.items() if k != "slug"}
    clean["environments"] = [{k: v for k, v in e.items() if k in ("name", "base", "user", "compare")}
                             for e in profile.get("environments") or []]
    CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
    p = _path(slug)
    p.write_text(json.dumps(clean, indent=2, ensure_ascii=False))
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    if passwords and _keyring:
        for env, pw in passwords.items():
            if pw:
                _keyring.set_password(KEYRING_SERVICE, f"{slug}/{env}", pw)
    return slug


def get_password(slug, env):
    if not _keyring:
        return None
    try:
        return _keyring.get_password(KEYRING_SERVICE, f"{slugify(slug)}/{env}")
    except Exception:
        return None


def delete(slug):
    prof = load(slug)
    if prof and _keyring:
        for e in prof.get("environments") or []:
            try:
                _keyring.delete_password(KEYRING_SERVICE, f"{slugify(slug)}/{e.get('name')}")
            except Exception:
                pass
    p = _path(slug)
    if p.exists():
        p.unlink()


# ── Evaluación de instancias ────────────────────────────────────────────

def normalize_base(url):
    """'xxx.fa.em2.oraclecloud.com/fscmUI/...' → 'https://xxx.fa.em2.oraclecloud.com'."""
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"(?i)https?://", url):
        url = "https://" + url
    u = urlparse(url)
    return f"{u.scheme.lower()}://{u.netloc.lower()}"


def suggest_env_name(base):
    """Propone un nombre de entorno a partir del host (xxx-dev1.fa… → DEV1, xxx.fa… → PROD)."""
    host = urlparse(base).netloc.split(".")[0]
    m = re.search(r"-([a-z]+\d*)$", host)
    return m.group(1).upper() if m else "PROD"


def probe(base):
    """Comprueba sin credenciales que la URL es una instancia Fusion con BI Publisher.
    El endpoint SOAP responde 401 a una petición anónima si existe."""
    base = normalize_base(base)
    out = {"base": base, "suggested_name": suggest_env_name(base) if base else "", "ok": False}
    if not base:
        out["message"] = "URL vacía."
        return out
    t0 = time.time()
    try:
        r = fbip.requests.post(fbip.endpoint(base), data=b"",
                               headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                               timeout=20)
    except Exception as e:
        out["message"] = f"No responde: {e.__class__.__name__}"
        return out
    out["latency_ms"] = int((time.time() - t0) * 1000)
    out["status"] = r.status_code
    if r.status_code in (401, 403) or (r.status_code == 500 and "Envelope" in r.text):
        out["ok"] = True
        out["message"] = "Instancia Fusion accesible (BI Publisher responde)."
    elif r.status_code == 404:
        out["message"] = "El host responde pero no expone BI Publisher (HTTP 404). ¿Es una URL de Fusion?"
    else:
        out["message"] = f"No parece una instancia Oracle Fusion (HTTP {r.status_code} en BI Publisher)."
    return out


def check_login(base, user, pw):
    """Valida usuario/contraseña contra el catálogo BI Publisher."""
    base = normalize_base(base)
    if not base or not user or not pw:
        return (False, "Faltan URL, usuario o contraseña.")
    body = "<pub:getFolderContents><pub:folderAbsolutePath>/</pub:folderAbsolutePath></pub:getFolderContents>"
    try:
        xml = fbip.soap_call(base, user, pw, body, timeout=40)
    except Exception as e:
        msg = str(e)
        if "401" in msg:
            return (False, "Usuario o contraseña incorrectos (401).")
        return (False, f"No se pudo conectar: {msg[:300]}")
    if "getFolderContentsReturn" in xml or "<absolutePath" in xml:
        return (True, "OK")
    return (False, "Respuesta inesperada del endpoint BI Publisher.")


def check_sql(base, user, pw, report=None):
    """Comprueba que el report ejecutor de SQL existe y devuelve un resumen de la instancia."""
    report = report or fbip.SQL_REPORT_DEFAULT
    sql = ("SELECT (SELECT COUNT(*) FROM GL_LEDGERS) ledgers, "
           "(SELECT COUNT(*) FROM FUN_ALL_BUSINESS_UNITS_V WHERE status='A') bus, "
           "(SELECT COUNT(*) FROM XLE_ENTITY_PROFILES) les FROM dual")
    try:
        _, rows = fbip.parse_rows(fbip.run_sql(base, user, pw, report, sql, timeout=90))
    except Exception as e:
        msg = str(e)
        hint = ""
        if re.search(r"(?i)not found|no existe|does not exist|reportBytes|PathNotFound|Invalid report", msg):
            hint = (f" No se encuentra el report {report}: hay que desplegar el data model "
                    "SQLConDM y el report ejecutor (fusion-client setup) en esta instancia.")
        return {"ok": False, "message": (msg.splitlines() or [""])[0][:300] + hint}
    r = rows[0] if rows else {}
    return {"ok": True, "ledgers": r.get("LEDGERS"), "bus": r.get("BUS"), "legal_entities": r.get("LES")}
