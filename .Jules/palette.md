## 2026-10-19 - Accessible Form Controls and Icon Buttons
**Learning:** In Jinja templates, form inputs without explicit `id` attributes matched to `for` attributes on labels (or icon buttons without `aria-label` and `aria-hidden` attributes) cause critical accessibility failures for screen readers. Using `title` attributes alone is insufficient for screen readers.
**Action:** Always verify proper `for`/`id` bindings on forms and use `aria-label`s on icon-only buttons with `aria-hidden="true"` on the visual icons themselves when making UI components.
