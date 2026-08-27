---
name: frontend-aksel
description: Preset for oppgaver som bygger eller endrer UI-komponenter med Nav sitt Aksel Design System
license: MIT
compatibility: Next.js/React med @navikt/ds-react (Aksel v8+)
metadata:
  domain: frontend
  tags: aksel design-system react nextjs planlegger-preset
---

# Frontend+Aksel preset

Brukes av `planlegger` når en oppgave bygger eller endrer UI med Aksel Design System.

## Trigger

Oppgaven nevner **minst én** av:
- en UI-komponent (knapp, skjema, modal, tabell, kort, varsel, layout)
- Aksel, designsystem, `@navikt/ds-react` eller `@navikt/aksel-*`
- en Figma-lenke eller "implementer dette designet"

## Default sti

- Rene, isolerte komponent-tillegg som følger etablert mønster i samme mappe:
  `Sti=enkel`, `Krever planreview=nei`.
- Nye sider, layout-endringer på tvers av flere komponenter, eller endringer som
  påvirker tilgjengelighet/temaer (dark mode) bredt: `Sti=komplisert`,
  `Krever planreview=ja`.

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **Komponentvalg**: hvilke Aksel-komponenter/layout-primitiver brukes
  (`Box`/`HStack`/`VStack`/`HGrid`), og hvorfor ikke egendefinert CSS/HTML.
- **Spacing/tokens**: bruk Aksel sine spacing-tokens og `ResponsiveProp` for
  responsivt design, ikke hardkodede piksel-verdier.
- **Tilgjengelighet**: hvilke ARIA-attributter/semantisk HTML kreves (Aksel-
  komponenter er tilgjengelige som standard — ikke overstyr det med rå `div`/`span`
  uten grunn).
- **Versjon**: hvilken Aksel-versjon prosjektet faktisk bruker (sjekk
  `package.json` — API kan ha endret seg mellom major-versjoner).

## Sjekkliste for koder

- [ ] Bruker Aksel-komponenter/layout-primitiver fremfor egendefinert HTML/CSS der
      et tilsvarende Aksel-mønster finnes.
- [ ] Spacing bruker Aksel sine tokens (`space-*`), ikke hardkodet CSS.
- [ ] Responsivt design bruker `ResponsiveProp` der det er naturlig, ikke egne
      media queries.
- [ ] Ingen `!important` eller CSS-overstyring av Aksel sine interne klassenavn.
- [ ] Farger/tema hentes fra Aksel sine design tokens, ikke hardkodede hex-verdier.
- [ ] Tekstinnhold følger klarspråk/Nav-tone (se `norwegian-text`-instruksjoner hvis
      relevant), ikke maskinoversatt eller unaturlig norsk.

## Ikke gjør

- Ikke bygg egne varianter av komponenter Aksel allerede tilbyr (knapper, inputs,
  alerts, modaler) uten eksplisitt begrunnelse i brief.
- Ikke hardkod farger, avstand eller font-størrelser utenom Aksel sine tokens.
- Ikke fjern eller overstyr tilgjengelighetsattributter Aksel-komponenter setter
  som standard.
