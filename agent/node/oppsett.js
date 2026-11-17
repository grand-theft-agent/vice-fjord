// Oppsettet som agent.js og sjekk.js deler: .env, modellen og klienten.
import path from 'node:path';
import Anthropic from '@anthropic-ai/sdk';

// .env ligger i roten av repoet, felles for Node og Python.
try {
  process.loadEnvFile(path.join(import.meta.dirname, '..', '..', '.env'));
} catch {
  // Ingen .env. Da må ANTHROPIC_API_KEY være satt i miljøet.
}

// Regel 4: adressen, oppdraget, varianten og crewkoden står her og ikke i koden.
// Byen kjører hostet på byen.hackaton.dev. Sier Syndikatet fra om en nødby, bytter dere BYEN_URL.
export const STANDARD_BY = 'https://byen.hackaton.dev';
export const BYEN_URL = (process.env.BYEN_URL || STANDARD_BY).replace(/\/+$/, '');
export const OPPDRAG = process.argv[2] || process.env.OPPDRAG || 'kureren';
export const VARIANT = process.env.VARIANT || 'vanlig';
export const CREW = (process.env.CREW || '').trim();
// Et kort merke på kjøringen (høyst 40 tegn), så den er lett å kjenne igjen i byvisningen og på tavlen.
export const MERKE = process.env.MERKE || '';

export const MODELL = process.env.MODELL || 'claude-sonnet-5-5';
export const EFFORT = process.env.EFFORT || 'medium';

// Stopper en agent som går i ring før den brenner opp nøkkelen.
// Én iterasjon er ett svar fra modellen, med så mange verktøykall som den ber om.
export const MAX_ITERASJONER = Number(process.env.MAX_ITERASJONER || 50);

// Haiku 4.5 og eldre modeller kan ikke styres med effort.
export function medEffort(forespørsel, effort = EFFORT) {
  if (/haiku-4|claude-3/.test(forespørsel.model)) return forespørsel;
  return { ...forespørsel, output_config: { ...forespørsel.output_config, effort } };
}

// Byen vil ha crewkoden i headeren X-Crew. Den står på lappen fra Syndikatet.
export const MANGLER_CREW = 'Sett CREW i .env til crewkoden fra lappen.';
export function krevCrew() {
  if (!CREW) throw new Error(`Mangler crewkoden. ${MANGLER_CREW}`);
}

// Fikk ikke kontakt med byen i det hele tatt (ingen HTTP-svar).
export const INGEN_KONTAKT = `Fikk ikke kontakt med byen på ${BYEN_URL}. Sjekk nettet og BYEN_URL i .env (standard ${STANDARD_BY}).`;

let klient;
export function hentKlient() {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error('Mangler ANTHROPIC_API_KEY. Kopier .env.example til .env i roten av repoet og lim inn nøkkelen.');
  }
  return (klient ??= new Anthropic());
}

// Feil fra modell-API-et, forklart så crewet vet hva de skal gjøre.
export function forklar(e) {
  const adresse = process.env.ANTHROPIC_BASE_URL || 'https://api.anthropic.com';
  if (e instanceof Anthropic.AuthenticationError) {
    return 'Nøkkelen ble avvist (401). Sjekk at hele nøkkelen er limt inn i .env, uten mellomrom eller anførselstegn.';
  }
  if (e instanceof Anthropic.PermissionDeniedError) return `Nøkkelen har ikke tilgang (403): ${e.message}`;
  if (e instanceof Anthropic.NotFoundError) {
    return `Fant ikke modellen «${MODELL}» (404). Sett MODELL i .env til en modell nøkkelen har tilgang til.`;
  }
  if (e instanceof Anthropic.RateLimitError) return 'For mange kall eller tomt for kreditt (429). Vent litt og prøv igjen.';
  if (e instanceof Anthropic.APIConnectionError) return `Kom ikke fram til ${adresse}. Sjekk nettet, VPN og eventuell proxy.`;
  if (e instanceof Anthropic.APIError) return `Modell-API-et svarte ${e.status}: ${e.message}`;
  return e.message;
}

// ── Farger i terminalen ──
const farge = (k) => (t) => (process.stdout.isTTY ? `\x1b[${k}m${t}\x1b[0m` : String(t));
export const grå = farge('90');
export const rosa = farge('1;38;5;205');
export const neon = farge('1;38;5;51');
export const oransje = farge('38;5;208');
export const grønn = farge('1;32');
export const gul = farge('38;5;220');
