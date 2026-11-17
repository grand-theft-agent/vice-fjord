#!/usr/bin/env node
// npm run sjekk: viser at nøkkelen, modellen, byen og crewkoden virker, eller sier hva som er galt.
// Kjør den før dere begynner, ikke når klokken er 16:25.
import { BYEN_URL, CREW, INGEN_KONTAKT, MANGLER_CREW, MODELL, forklar, hentKlient, medEffort } from './oppsett.js';

console.log(`Modell:  ${MODELL}`);
console.log(`Adresse: ${process.env.ANTHROPIC_BASE_URL || 'https://api.anthropic.com'}`);
console.log(`Byen:    ${BYEN_URL}${CREW ? ' (med crewkode)' : ' (uten crewkode)'}`);

let feil = 0;

try {
  const svar = await hentKlient().messages.create(medEffort({
    model: MODELL,
    max_tokens: 1000,
    messages: [{ role: 'user', content: 'Svar med ett ord: ok' }],
  }, 'low'));
  const tekst = svar.content.filter((b) => b.type === 'text').map((b) => b.text).join('').trim();
  console.log(`\n✓ Modellen svarte «${tekst}».`);
} catch (e) {
  console.error(`\n✖ ${forklar(e)}`);
  feil = 1;
}

// Først om byen svarer i det hele tatt (uten kode svarer den 401, og det er også et svar),
// så om crewkoden slipper inn: GET /oppdrag med X-Crew.
let byenSvarer = false;
try {
  await fetch(`${BYEN_URL}/`, { headers: { accept: 'application/json' }, signal: AbortSignal.timeout(15000) });
  byenSvarer = true;
  console.log('✓ Byen svarer.');
} catch {
  console.error(`✖ ${INGEN_KONTAKT}`);
  feil = 1;
}

if (!CREW) {
  console.error(`✖ Mangler crewkoden. ${MANGLER_CREW}`);
  feil = 1;
} else if (byenSvarer) {
  try {
    const r = await fetch(`${BYEN_URL}/oppdrag`, { headers: { 'x-crew': CREW }, signal: AbortSignal.timeout(15000) });
    const data = await r.json().catch(() => ({}));
    if (r.status === 401) throw new Error('Byen kjenner ikke crewkoden (401). Sjekk CREW i .env mot lappen; store og små bokstaver teller.');
    if (!r.ok) throw new Error(`Byen svarte ${r.status}: ${data.feil ?? ''}`);
    console.log(`✓ Crewkoden virker. Oppdrag: ${data.oppdrag.map((o) => o.id).join(', ')}.`);
  } catch (e) {
    console.error(`✖ ${e.name === 'TimeoutError' || e.name === 'TypeError' ? INGEN_KONTAKT : e.message}`);
    feil = 1;
  }
}

if (!feil) console.log('\nVice Fjord venter. Kjør npm run agent.');
process.exit(feil);
