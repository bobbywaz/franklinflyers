## 2026-10-06 - Icon-Only Buttons Require ARIA Labels
**Learning:** Using a `title` attribute on an icon-only button is insufficient for accessibility, as screen readers may not reliably read it. We must use an explicit `aria-label` on the button itself and set `aria-hidden="true"` on the visual icon to prevent redundant or confusing screen reader output.
**Action:** Always add `aria-label` to icon-only buttons and hide the internal decorative icon using `aria-hidden="true"`.
