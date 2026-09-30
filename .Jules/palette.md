## 2026-09-30 - Form Accessibility and Label Associations
**Learning:** Older templates and form structures in the project occasionally missed standard accessibility associations like `for` and `id` bindings on form inputs and `aria-label`s on icon-only buttons. Correctly mapping these enhances screen-reader usability.
**Action:** Always ensure that form inputs have explicitly associated labels via `id` and `for` attributes and that icon-only interactive elements contain `aria-label` or `aria-hidden` where appropriate to comply with standard accessibility practices.
