## 2026-10-23 - Found some icon buttons lacking aria labels

## 2026-10-23 - Accessibility improvements for inputs and icon buttons
**Learning:** HTML forms lack proper accessibility associations like `for`/`id` bindings and visual icons inside icon-only buttons need to be explicitly hidden using `aria-hidden="true"` with a parent `aria-label`.
**Action:** Ensure adherence to semantic accessibility standards by checking inputs for labels with `for` bindings, and `aria-label` attributes on icon-only interactive elements along with `aria-hidden` on the visual icon.
