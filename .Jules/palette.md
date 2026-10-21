## 2024-05-19 - Form Label Accessibility
**Learning:** Missing explicit label-to-input association in forms negatively impacts screen reader users and affects focus capabilities.
**Action:** Always verify custom form controls (e.g. text inputs) are properly wrapped or associated using explicit `for` and `id` attributes, and hide purely visual icons with `aria-hidden="true"`.
