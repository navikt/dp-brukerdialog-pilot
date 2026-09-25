---
name: brukerdialog-persondata
description: Preset for oppgaver som håndterer fødselsnummer, aktør-id eller annen sensitiv persondata
license: MIT
compatibility: Nav-applikasjoner som behandler persondata
metadata:
  domain: auth
  tags: persondata gdpr logging pii planlegger-preset
---

# Persondata preset

Brukes av `planlegger` når en oppgave berører fødselsnummer, aktør-id, adresse, navn, journal
eller andre sensitive felt.

## Trigger

Oppgaven nevner fødselsnummer, aktør-id, adresse, navn, journal eller sensitive felt.

## Default sti

- `Sti=komplisert`
- `Krever planreview=ja`

En konkret bestilling om å lagre, lese eller behandle persondata på en tydelig
beskrevet måte er **ikke** i seg selv et stopp-punkt — planreview og
sjekklisten under dekker det. Stopp og be om bekreftelse (se planleggers
"Risikotrigger vs. stopp-punkt") kun når oppgaven faktisk medfører logging
eller unødvendig eksponering av persondata (f.eks. å returnere fødselsnummer
i et API-svar uten at oppgaven ber om det), eller når det er uklart hvem som
skal ha tilgang.

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **Logging-maskering**: eksplisitt hvilke felt som IKKE skal i vanlig logg, og hvor
  sikkerlogg/persondata-logg brukes i stedet.
- **Tilgangskontroll**: hvem/hva har lov til å lese dataene (bruker selv, saksbehandler med
  riktig rolle, systembruker)? Verifiser eierskap før respons, ikke bare autentisering.
- **Eksplisitte verifiseringspunkter**: konkrete kommandoer/steg for å bekrefte at persondata
  ikke lekker (f.eks. grep i loggutdata, sjekk av response-body i test).

## Sjekkliste for koder

- [ ] Fødselsnummer, aktør-id, navn, adresse og tokens logges aldri i vanlig logg.
- [ ] Sikkerlogg (eller tilsvarende persondata-logg) brukes for feilsøkingskontekst med PII.
- [ ] Request/response-bodyer med persondata logges ikke ved feil (ingen catch-all som logger
  hele exception-konteksten inkl. payload).
- [ ] Tilgangskontroll sjekker eierskap (IDOR), ikke bare at token er gyldig.
- [ ] Feilmeldinger til klient inneholder ikke sensitiv kontekst (bruk generiske meldinger,
  logg detaljer server-side i sikkerlogg).

## Ikke gjør

- Ikke deleger uten at bruker har bekreftet stopp-punktet eksplisitt.
- Ikke logg persondata "midlertidig for debugging" — bruk sikkerlogg i stedet.
- Ikke eksponer persondata i valideringsfeil (f.eks. `@Pattern`-annotasjoner som ekko-er
  brukerinput i feilmeldingen).

## Ved eksplisitt forsøk på å logge persondata i vanlig logg

Hvis bruker eksplisitt ber om å logge fødselsnummer, aktør-id, navn, adresse eller tokens i
vanlig logg: avvis oppgaven direkte (`avvist`), ikke eskaler til planreview eller deleger.
