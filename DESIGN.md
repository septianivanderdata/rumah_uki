# Unit Kepatuhan Internal — Visual system

This redesign adapts the visual direction of [Bou](https://wearebou.com/) to an internal compliance portal: immersive photography, restrained monochrome colors, light sans-serif headings, generous spacing and simple document links. The four static HTML pages share `assets/site.css` and `assets/site.js`.

## Colors and typography

- Carbon `#101310`: primary text and footer.
- White `#ffffff`: page canvas and hero text.
- Mist `#f4f5f2`: service illustrations and document cards.
- Stone `#dfe2dc`: borders.
- Muted `#626760`: secondary text.
- Maritime `#36534b`: document illustration accents.

Manrope 400/500 is used for display text; DM Sans 400/500/600 is used for body text and navigation. Fonts load from Google Fonts with Arial fallback. Headings use responsive sizes and slightly tightened letter spacing.

## Layout and interaction

Desktop pages use a centered maximum content width of 1320px and 56px side margins. Tablet margins are 32px; phone margins are 20px. The homepage opens with a full-viewport harbor photo and centered introductory statement. The service section has three cards, followed by compliance pillars and existing announcements. Inner pages organize reporting steps, reference documents and unit links under large left-aligned titles.

All pages include the same mobile menu, active page indicator, skip link, keyboard focus styles and footer. Navigation collapses below 1001px. Menus close on link selection, outside click, Escape and desktop resize. Reveal effects respect reduced-motion preferences; content is visible without JavaScript. External document links retain their original destinations; placeholder months are shown as “Belum tersedia”.

## Assets

`assets/harbor.jpg` is an illustrative harbor photograph from [Unsplash](https://images.unsplash.com/photo-1578575437130-527eed3abbec). It is not presented as a photograph of Teluk Nibung. Service document illustrations are original inline SVGs. No Bou photography, video, fonts or logo assets are copied.

## Preview

Run `python3 -m http.server 8765 --bind 127.0.0.1` from the project root and open `http://127.0.0.1:8765/`. This is a static site with no build step.
