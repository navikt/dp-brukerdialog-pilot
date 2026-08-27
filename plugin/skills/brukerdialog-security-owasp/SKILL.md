---
name: brukerdialog-security-owasp
description: Preset for oppgaver som berører tilgangskontroll, injeksjon, kryptering, forsyningskjede eller feilhåndtering utover det persondata-presetet dekker
license: MIT
compatibility: Kotlin/Ktor, Go, Java, Node.js på Nais
metadata:
  domain: security
  tags: security owasp access-control injection supply-chain planlegger-preset
---

# Security-OWASP-preset

Brukes av `planlegger` når en oppgave berører sikkerhetsmønstre fra OWASP Top 10:2025
som ikke allerede dekkes av `brukerdialog-persondata` (logging/PII-håndtering) eller
planleggers generiske auth-stopp-punkt. Basert på det etablerte
`security-owasp`-skillet — dette presetet er den korte, `planlegger`-spesifikke
versjonen som avgjør sti/planreview og tvinger inn brief-felt.

## Trigger

Oppgaven berører **minst én** av:
- tilgangskontroll på en spesifikk ressurs (IDOR: "hent `{id}` for innlogget bruker",
  eierskapssjekk), ikke bare autentisering generelt
- SQL/kommando-bygging fra brukerinput (fare for injeksjon)
- CORS-konfigurasjon
- pinning/oppdatering av dependencies eller GitHub Actions-versjoner
- kryptografi (TLS-verifisering, hashing, signering)
- feilhåndtering som kan skjule eller eksponere sensitiv informasjon til klient

## Default sti

- `Sti=komplisert`
- `Krever planreview=ja`
- **Alltid stopp-punkt før delegasjon** når oppgaven gjelder tilgangskontroll/IDOR
  eller kryptografi — dette faller inn under planleggers eksisterende
  auth/autorisasjon-stopp-punkt. For injeksjon/CORS/supply chain uten en
  tilgangskontroll-komponent holder det med planreview (ikke nødvendigvis
  stopp-punkt), men vurder fail-closed hvis usikker.

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **Eierskapssjekk (IDOR)**: for enhver `{id}`-basert ressurstilgang — eksplisitt
  hvordan koden verifiserer at innlogget bruker/system faktisk eier eller har rett
  til ressursen, ikke bare at et gyldig token er til stede.
- **Parameteriserte spørringer**: alle SQL-kall skal bruke `?`/named parameters
  (Kotliquery), aldri string-interpolering av brukerinput inn i SQL-tekst. Tilsvarende
  for shell-kommandoer: aldri brukerinput inn i en shell-streng, alltid som separate
  argumenter.
- **CORS-scope**: eksakt hvilke origins som tillates — aldri `anyHost()`/`*`.
- **Feilrespons til klient**: generisk feilmelding uten stack trace, SQL-feil eller
  filstier; detaljer logges server-side (sikkerlogg hvis persondata er involvert).
- **Dependency-pinning** (hvis relevant): eksakt versjon/SHA som pinnes, og hvorfor
  (sikkerhetsoppdatering, kjent sårbarhet).

## Sjekkliste for koder

- [ ] Ressurstilgang med `{id}` sjekker eierskap, ikke bare at token er gyldig (IDOR).
- [ ] Ingen SQL bygget med string-interpolering av brukerinput — alltid
      parameteriserte spørringer.
- [ ] Ingen shell-kommando kjøres med ukontrollert brukerinput i kommandostrengen.
- [ ] CORS er begrenset til kjente origins, ikke `anyHost()`/`*`.
- [ ] Feilmeldinger til klient inneholder ikke stack traces, SQL-feiltekst eller
      filstier.
- [ ] Nye/endrede GitHub Actions-steg er pinnet til full SHA, ikke `@main`/flytende tag.
- [ ] Feil håndteres eksplisitt (ingen stille `catch`-blokker som svelger unntak uten
      logging eller propagering).
- [ ] Ingen `InsecureSkipVerify`/tilsvarende TLS-verifiseringsbypass.

## Ikke gjør

- Ikke stol på at et gyldig token er nok — sjekk alltid eierskap/rolle for den
  spesifikke ressursen som forespørres.
- Ikke bygg SQL eller shell-kommandoer med string-konkatenering av brukerinput.
- Ikke sett CORS til å tillate alle origins for å "unngå CORS-feil raskt".
- Ikke la feilhåndtering lekke interne detaljer (stack traces, SQL, filstier) til
  klienten.
- Ikke deaktiver TLS-verifisering, selv midlertidig for feilsøking.
