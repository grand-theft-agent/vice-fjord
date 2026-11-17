"""Oppsettet som agent.py og sjekk.py deler: .env, modellen, klienten og byen."""

import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

import anthropic


def _les_env(fil: Path) -> None:
    """Leser .env uten ekstra pakker. Det som alt står i miljøet, vinner."""
    if not fil.exists():
        return
    for linje in fil.read_text(encoding="utf-8").splitlines():
        linje = linje.strip()
        if not linje or linje.startswith("#") or "=" not in linje:
            continue
        nøkkel, verdi = linje.split("=", 1)
        os.environ.setdefault(nøkkel.strip(), verdi.strip().strip("\"'"))


# .env ligger i roten av repoet, felles for Node og Python.
_les_env(Path(__file__).resolve().parent.parent.parent / ".env")

# Regel 4: adressen, oppdraget, varianten og crewkoden står her og ikke i koden.
# Byen kjører hostet på byen.hackaton.dev. Sier Syndikatet fra om en nødby, bytter dere BYEN_URL.
STANDARD_BY = "https://byen.hackaton.dev"
BYEN_URL = (os.environ.get("BYEN_URL") or STANDARD_BY).rstrip("/")
OPPDRAG = (sys.argv[1] if len(sys.argv) > 1 else None) or os.environ.get("OPPDRAG") or "kureren"
VARIANT = os.environ.get("VARIANT") or "vanlig"
CREW = (os.environ.get("CREW") or "").strip()
# Et kort merke på kjøringen (høyst 40 tegn), så den er lett å kjenne igjen i byvisningen og på tavlen.
MERKE = os.environ.get("MERKE") or ""

MODELL = os.environ.get("MODELL") or "claude-sonnet-5-5"
EFFORT = os.environ.get("EFFORT") or "medium"

# Stopper en agent som går i ring før den brenner opp nøkkelen.
# Én iterasjon er ett svar fra modellen, med så mange verktøykall som den ber om.
MAX_ITERASJONER = int(os.environ.get("MAX_ITERASJONER") or 50)


def med_effort(forespørsel: dict, effort: str = EFFORT) -> dict:
    """Haiku 4.5 og eldre modeller kan ikke styres med effort."""
    if re.search(r"haiku-4|claude-3", forespørsel["model"]):
        return forespørsel
    return {**forespørsel, "output_config": {**forespørsel.get("output_config", {}), "effort": effort}}


# Byen vil ha crewkoden i headeren X-Crew. Den står på lappen fra Syndikatet.
MANGLER_CREW = "Sett CREW i .env til crewkoden fra lappen."

# Fikk ikke kontakt med byen i det hele tatt (ingen HTTP-svar).
INGEN_KONTAKT = f"Fikk ikke kontakt med byen på {BYEN_URL}. Sjekk nettet og BYEN_URL i .env (standard {STANDARD_BY})."


def krev_crew() -> None:
    if not CREW:
        raise RuntimeError(f"Mangler crewkoden. {MANGLER_CREW}")


_klient = None


def hent_klient() -> anthropic.Anthropic:
    global _klient
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("Mangler ANTHROPIC_API_KEY. Kopier .env.example til .env i roten av repoet og lim inn nøkkelen.")
    if _klient is None:
        _klient = anthropic.Anthropic()
    return _klient


def forklar(e: Exception) -> str:
    """Feil fra modell-API-et, forklart så crewet vet hva de skal gjøre."""
    adresse = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    if isinstance(e, anthropic.AuthenticationError):
        return "Nøkkelen ble avvist (401). Sjekk at hele nøkkelen er limt inn i .env, uten mellomrom eller anførselstegn."
    if isinstance(e, anthropic.PermissionDeniedError):
        return f"Nøkkelen har ikke tilgang (403): {e}"
    if isinstance(e, anthropic.NotFoundError):
        return f"Fant ikke modellen «{MODELL}» (404). Sett MODELL i .env til en modell nøkkelen har tilgang til."
    if isinstance(e, anthropic.RateLimitError):
        return "For mange kall eller tomt for kreditt (429). Vent litt og prøv igjen."
    if isinstance(e, anthropic.APIConnectionError):
        return f"Kom ikke fram til {adresse}. Sjekk nettet, VPN og eventuell proxy."
    if isinstance(e, anthropic.APIStatusError):
        return f"Modell-API-et svarte {e.status_code}: {e}"
    return str(e)


class IngenBy(Exception):
    pass


def _ssl() -> ssl.SSLContext:
    """Sertifikatene til https://byen.hackaton.dev. Python fra python.org på macOS har ingen egne,
    så vi bruker certifi, som følger med anthropic-pakken (samme som modellkallene bruker)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


SSL = _ssl()

# Cloudflare avviser urllib sin egen User-Agent («Python-urllib», feil 1010), så agenten sier hvem den er.
USER_AGENT = "vice-fjord-agent/1.0 (python)"


def åpne(forespørsel: urllib.request.Request, timeout: float = 30):
    """urlopen med sertifikatene og User-Agent over. Brukes av byen() og sjekk.py."""
    forespørsel.add_header("User-Agent", USER_AGENT)
    return urllib.request.urlopen(forespørsel, timeout=timeout, context=SSL)


def byen(metode: str, sti: str, kropp: dict | None = None, timeout: float = 30, ekstra: dict | None = None) -> tuple[bool, dict]:
    """Ett kall til byen. Gir (ok, data), der data har «feil» når noe gikk galt."""
    headere = {"content-type": "application/json", "x-crew": CREW, **(ekstra or {})}
    data_ut = json.dumps(kropp).encode() if kropp is not None else None
    forespørsel = urllib.request.Request(f"{BYEN_URL}{sti}", data=data_ut, headers=headere, method=metode)
    try:
        with åpne(forespørsel, timeout) as svar:
            status, tekst = svar.status, svar.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        status, tekst = e.code, e.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise IngenBy(INGEN_KONTAKT + ssl_hint(e))
    try:
        data = json.loads(tekst)
    except json.JSONDecodeError:
        data = {"feil": tekst[:300] or f"Tomt svar ({status})"}
    ok = 200 <= status < 300
    if not ok:
        hint = " Sjekk CREW i .env mot crewkoden på lappen." if status == 401 else ""
        data = {**data, "feil": f"Byen svarte {status}: {data.get('feil', tekst)}{hint}"}
    return ok, data


def ssl_hint(e: Exception) -> str:
    if "CERTIFICATE_VERIFY_FAILED" in str(e):
        return " Python mangler sertifikatene: kjør pip install certifi i samme miljø (eller «Install Certificates» på macOS)."
    return ""


# ── Farger i terminalen ──
def _farge(kode: str):
    return lambda t: f"\x1b[{kode}m{t}\x1b[0m" if sys.stdout.isatty() else str(t)


grå = _farge("90")
rosa = _farge("1;38;5;205")
neon = _farge("1;38;5;51")
oransje = _farge("38;5;208")
grønn = _farge("1;32")
gul = _farge("38;5;220")
