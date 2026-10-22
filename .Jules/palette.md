## 2024-10-22 - [Proper ARIA labels on Icon Buttons and Explicit Form Labels]
**Learning:** Icon-only buttons relying solely on `title` tags lack screen-reader support. Native explicit form label associations (`for`/`id` bindings) are crucial for accessibility and interaction hitboxes.
**Action:** Always wrap visual icons inside an `aria-hidden="true"` span and provide a descriptive `aria-label` to the outer `<button>` when text is omitted. Always ensure form `<label>`s use `for` matching the `<input id>`.
