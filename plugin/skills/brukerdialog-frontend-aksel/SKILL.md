---
name: brukerdialog-frontend-aksel
description: Preset for oppgaver som bygger eller endrer UI-komponenter med Nav sitt Aksel Design System
license: MIT
compatibility: Next.js/React med @navikt/ds-react (Aksel v8+)
metadata:
  domain: frontend
  tags: aksel design-system react nextjs planlegger-preset
---

# Frontend+Aksel preset

Brukes av `planlegger` når en oppgave bygger eller endrer UI med Aksel Design System.
Basert på det etablerte `aksel-builder`-skillet (Nav MCP-basert Aksel-ekspert) — dette
presetet er den korte, `planlegger`-spesifikke versjonen som avgjør sti/planreview og
tvinger inn brief-felt; `koder` bør fortsatt bruke `aksel-builder` (eller Aksel MCP) direkte
for selve implementasjonen.

## Trigger

Oppgaven nevner **minst én** av:
- en UI-komponent (knapp, skjema, modal, tabell, kort, varsel, layout)
- Aksel, designsystem, `@navikt/ds-react` eller `@navikt/aksel-*`
- en Figma-lenke eller "implementer dette designet"

## Default sti

- Rene, isolerte komponent-tillegg som følger etablert mønster i samme mappe:
  `Sti=enkel`, `Krever planreview=nei`.
- Nye sider, layout-endringer på tvers av flere komponenter, endringer som påvirker
  tilgjengelighet/temaer (dark mode) bredt, eller Figma-til-kode-oppgaver:
  `Sti=komplisert`, `Krever planreview=ja`.

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **MCP-first**: minn `koder` på at Aksel-API (props, tokens, ikonnavn) skal bekreftes
  via Aksel MCP (`aksel_*`-verktøy) eller `https://aksel.nav.no/llm.md` hvis MCP ikke er
  tilgjengelig — **ikke** generert fra hukommelse. Aksel endrer API mellom major-versjoner,
  og feil her er en vanlig kilde til at kode ser riktig ut men bruker en API som ikke
  finnes lenger.
- **Komponentvalg**: hvilke Aksel-komponenter/layout-primitiver brukes
  (`Box`/`HStack`/`VStack`/`HGrid`/`Page`/`Bleed`), og hvorfor ikke egendefinert CSS/HTML.
- **Tokens fremfor rå verdier**: spacing, farger og radius skal komme fra Aksel sine
  design tokens (token-props eller `--ax-`-variabler), ikke hardkodet hex/piksel.
- **Tilgjengelighet**: hvilke ARIA-attributter/semantisk HTML kreves. Aksel-komponenter
  er tilgjengelige som standard — ikke overstyr det med rå `div`/`span` uten grunn.
- **Versjon**: hvilken Aksel-versjon prosjektet faktisk bruker (sjekk `package.json` for
  `@navikt/ds-react`) — API kan ha endret seg mellom major-versjoner (se
  migreringsguide v7→v8 hvis relevant).

## Sjekkliste for koder

- [ ] Alle Aksel-komponenter, props, tokens og ikonnavn er bekreftet via MCP eller
      `aksel.nav.no`-dokumentasjon, ikke antatt fra hukommelse.
- [ ] Bruker Aksel-komponenter/layout-primitiver fremfor egendefinert HTML/CSS der et
      tilsvarende Aksel-mønster finnes.
- [ ] Spacing/farger/radius bruker Aksel sine tokens, ikke hardkodet CSS.
- [ ] Responsivt design bruker `ResponsiveProp` der det er naturlig, ikke egne
      media queries.
- [ ] Ingen `!important` eller CSS-overstyring av Aksel sine interne klassenavn.
- [ ] Ikonimporter bruker `${navn}Icon`-eksporten fra `@navikt/aksel-icons`.
- [ ] Nødvendige a11y-props (labels, descriptions, alt-tekst) er til stede.
- [ ] Tekstinnhold følger klarspråk/Nav-tone, ikke maskinoversatt eller unaturlig norsk.

## Ikke gjør

- Ikke bygg egne varianter av komponenter Aksel allerede tilbyr (knapper, inputs,
  alerts, modaler) uten eksplisitt begrunnelse i brief.
- Ikke hardkod farger, avstand eller font-størrelser utenom Aksel sine tokens.
- Ikke fjern eller overstyr tilgjengelighetsattributter Aksel-komponenter setter
  som standard.
- Ikke finn opp doc-stier, prop-navn, token-navn eller ikon-eksporter — bekreft via
  MCP/dokumentasjon først.
