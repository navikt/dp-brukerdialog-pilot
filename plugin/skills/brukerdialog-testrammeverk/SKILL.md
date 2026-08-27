---
name: brukerdialog-testrammeverk
description: Preset for oppgaver som innfører eller setter opp et nytt testrammeverk, i motsetning til å legge til en enkelt test i et eksisterende oppsett
license: MIT
compatibility: Kotlin (Kotest/JUnit) og TypeScript (Vitest/Playwright)
metadata:
  domain: testing
  tags: testing vitest playwright kotest ci planlegger-preset
---

# Testrammeverk-preset

Brukes av `planlegger` når en oppgave **innfører** et testrammeverk fra bunnen av, ikke
når den bare legger til én test i et allerede fungerende oppsett. For selve Playwright-
oppsettet, se det etablerte `playwright-testing`-skillet (page objects, auth fixtures,
CI-config) — dette presetet avgjør sti/planreview og tvinger inn brief-felt for
`koder`, uansett hvilket rammeverk som innføres.

## Trigger

Oppgaven ber om å:
- sette opp/konfigurere et testrammeverk som ikke finnes i prosjektet ennå
  (Vitest, Playwright, Kotest, JUnit, Testcontainers, MockOAuth2Server)
- legge til test-runner i CI for første gang
- innføre en ny testtype prosjektet ikke har (f.eks. E2E når kun unit-tester finnes)

**Ikke** trigger: å legge til én ny testfil eller ett nytt testtilfelle i et
eksisterende, fungerende testoppsett — det er enkel sti som normalt.

## Default sti

- `Sti=komplisert`
- `Krever planreview=ja`

Default komplisert fordi det typisk innebærer nye dependencies, config-filer, og
endring i CI-workflow — alle er egne sikkerhetstriggere i `planlegger`.

## Obligatoriske brief-felt (i tillegg til standardfeltene)

Når dette presetet trigges, skal `KODER_BRIEF` alltid inneholde:

- **Rammeverksvalg og versjon**: nøyaktig hvilket bibliotek og versjon som
  introduseres, og hvorfor (følg eksisterende konvensjon i teamet/organisasjonen
  hvis én finnes, fremfor å velge fritt).
- **Struktur**: for Playwright, page object-mønster (`e2e/pages/*.page.ts`) og
  auth-fixture (Azure AD/MockOAuth2Server via cookie/token) i stedet for at hver test
  logger inn på nytt. For Kotlin, Kotest-matchers og `TestRapid` for Rapids & Rivers.
- **Locator-/matcher-strategi**: for Playwright, prioriter `getByRole`/`getByLabel`/
  `getByText` fremfor CSS-selektorer eller `getByTestId` (kun som siste utvei).
- **CI-integrasjon**: hvordan testene faktisk kjøres i CI (ny workflow-fil eller nytt
  steg i eksisterende workflow, inkl. `playwright install --with-deps` for E2E) — ikke
  bare lokalt kjørbare tester uten CI-kobling.
- **Scope for første PR**: rammeverksoppsett + **ett** eksempel-/smoke-test er nok i
  første leveranse. Ikke migrer all eksisterende testkode i samme endring.
- **Isolasjon**: nye testdependencies skal ikke lekke inn i produksjonsavhengigheter
  (`devDependencies`/`testImplementation`, ikke `dependencies`/`implementation`).

## Sjekkliste for koder

- [ ] Testdependencies er lagt til som dev-/test-scope, ikke produksjonsscope.
- [ ] Minst én eksempeltest kjører grønt lokalt og i CI før PR-en anses ferdig.
- [ ] Testnavn/struktur følger prosjektets/organisasjonens konvensjon (norsk
      backtick-navn for Kotlin, describe/it for TypeScript, given/when/then-struktur).
- [ ] For E2E: bruker `getByRole`/`getByLabel` som primær locator-strategi, ikke CSS-
      selektorer; unngår `page.waitForTimeout()` (Playwright venter implisitt).
- [ ] CI-workflowen feiler synlig (ikke stille) hvis en test feiler, og laster opp
      testrapport (f.eks. `playwright-report/`) som artifact ved feil.
- [ ] Ingen ekte secrets/credentials i test-fixtures — bruk fakes/mocks
      (MockOAuth2Server, Testcontainers, MSW) i stedet.

## Ikke gjør

- Ikke migrer eller omskriv all eksisterende testkode til det nye rammeverket i
  samme PR som setter det opp — gjør det trinnvis i senere, egne endringer.
- Ikke innfør et testrammeverk uten å koble det til CI i samme leveranse (et
  rammeverk ingen kjører automatisk gir falsk trygghet).
- Ikke velg et nytt, ukjent rammeverk hvis organisasjonen allerede har et etablert
  standardvalg for samme testtype.
- For E2E: ikke bruk `page.locator(".css-class")`/`#id`-selektorer når en rolle- eller
  label-basert locator finnes.
