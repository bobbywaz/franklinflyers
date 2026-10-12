## 2024-10-12 - Form Label and Icon Accessibility
**Learning:** Found pattern where HTML forms lack `for`/`id` bindings for labels/inputs, and decorative icons lack `aria-hidden="true"`, negatively impacting screen reader UX.
**Action:** Always ensure semantic accessibility bindings (`for`/`id`) are present for inputs, and decorative icons inside buttons are explicitly hidden from screen readers using `aria-hidden="true"`.
