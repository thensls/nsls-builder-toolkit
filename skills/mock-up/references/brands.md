# Brands for mock-ups

Pick one brand per page and never mix them. Reviewers read a crossed brand as a visible mistake.

| Surface | Brand | Where it's defined |
| --- | --- | --- |
| Anything inside Society, or a product built on it (member app, coach, school dashboard, partner or event pages members see) | **Society** | Below; live in `assets/example-coach-flow.html` |
| SLT or partner presentations, scrolling decks, proposal pages | **NSLS slide brand** | Below |
| A page meant to look like nsls.org | **NSLS web brand** | The `nsls-web-brand` skill (red, navy, Mulish) |

## Society

Light only, on purpose: it mirrors the member app.

```css
--paper:#f8f6f1;   /* page */          --panel:#ffffff;  /* cards, coach panel */
--card:#efebe3;    /* tiles, bubbles */ --ink:#1d1a17;    --muted:#6c665e;  --line:#e4dfd5;
--yellow:#f3d94e;  /* Society yellow, sampled from the "S" logo: selected states, highlights */
--espresso:#231a1c;/* the member's own chat bubble, solid buttons */
--pink:#e8b6e4; --lav:#969bde; --green:#8fd18b; /* prompt cards, avatars, done checks */
--red:#c8102e;     /* the concept banner only */
--serif:"Newsreader", Georgia, serif;    /* greetings, nav, headings */
--sans:"DM Sans", system-ui, sans-serif; /* everything else */
```

- **Fonts:** load both from Google Fonts.
- **Images:** the logo and the three track-card images are in `assets/img/`. Inline them as base64 data URIs, because artifacts can't load outside images.
- **App frame:** left nav (Home, Profile, Your coach, Achievements, then COMING SOON: Groups, Messages, Events, then Settings). The center reads "Hi {Name}," above three track cards and two prompt cards. The coach panel on the right holds the chat.
- **Selected state:** the selected scenario pill and any "you are here" chip use Society yellow with dark text.
- **Other-side views:** email and inbox views showing "what X receives" use a neutral system look (system-ui, grey bar). They're meant to read as the other person's inbox, not Society.

## NSLS slide brand

Use it for decks and SLT-facing pages, never for Society product screens.

```css
--navy:#18315a; --teal:#0091ae; --gold:#eeb117;
--display:"Lexend Deca", sans-serif; --body:"Nunito Sans", Avenir, sans-serif;
```

- **Scrolling deck:** full-viewport sections with scroll-snap, a dot rail on the right and a slide counter bottom-left.
- **Embedded mock-ups:** a live mock-up inside a slide runs in an iframe at 1440×810, scaled with a ResizeObserver. Give it an "Interact" toggle that switches pointer-events on, and a Replay that sends postMessage('nsls-replay').
