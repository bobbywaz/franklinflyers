## 2026-10-25 - HTML Forms Missing Semantic Bindings
**Learning:** Jinja templates in this app often use bare `<label>` or `<span>` elements without `for` attributes linked to the input's `id`, and icon-only buttons lack screen reader context, severely hindering accessibility.
**Action:** Always ensure `<label>` elements explicitly use the `for` attribute to bind to the `<input>` `id`, and use `aria-label`/`aria-hidden` on visual icons inside icon-only buttons.
