"""python agent/python/sjekk.py: viser at nøkkelen, modellen, byen og crewkoden virker,
eller sier hva som er galt. Kjør den før dere begynner, ikke når klokken er 16:25.
"""

import os
import sys
import urllib.error
import urllib.request

from oppsett import BYEN_URL, CREW, INGEN_KONTAKT, MANGLER_CREW, MODELL, IngenBy, ssl_hint, byen, forklar, hent_klient, med_effort, åpne

print(f"Modell:  {MODELL}")
print(f"Adresse: {os.environ.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')}")
print(f"Byen:    {BYEN_URL}{' (med crewkode)' if CREW else ' (uten crewkode)'}")

feil = 0

try:
    svar = hent_klient().messages.create(**med_effort({
        "model": MODELL,
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": "Svar med ett ord: ok"}],
    }, "low"))
    tekst = "".join(b.text for b in svar.content if b.type == "text").strip()
    print(f"\n✓ Modellen svarte «{tekst}».")
except Exception as e:
    print(f"\n✖ {forklar(e)}", file=sys.stderr)
    feil = 1

# Først om byen svarer i det hele tatt (uten kode svarer den 401, og det er også et svar),
# så om crewkoden slipper inn: GET /oppdrag med X-Crew.
byen_svarer = False
try:
    åpne(urllib.request.Request(f"{BYEN_URL}/", headers={"accept": "application/json"}), 15).close()
    byen_svarer = True
except urllib.error.HTTPError:
    byen_svarer = True
except (urllib.error.URLError, OSError) as e:
    print(f"✖ {INGEN_KONTAKT}{ssl_hint(e)}", file=sys.stderr)
    feil = 1
if byen_svarer:
    print("✓ Byen svarer.")

if not CREW:
    print(f"✖ Mangler crewkoden. {MANGLER_CREW}", file=sys.stderr)
    feil = 1
elif byen_svarer:
    try:
        ok, data = byen("GET", "/oppdrag", timeout=15)
        if not ok:
            if data["feil"].startswith("Byen svarte 401"):
                raise IngenBy("Byen kjenner ikke crewkoden (401). Sjekk CREW i .env mot lappen; store og små bokstaver teller.")
            raise IngenBy(data["feil"])
        print(f"✓ Crewkoden virker. Oppdrag: {', '.join(o['id'] for o in data['oppdrag'])}.")
    except IngenBy as e:
        print(f"✖ {e}", file=sys.stderr)
        feil = 1

if not feil:
    print("\nVice Fjord venter. Kjør python agent/python/agent.py.")
sys.exit(feil)
