## 2024-05-18 - Admin Accessibility Enhancements
**Learning:** Found that basic HTML templates for admin actions lacked screen reader associations, specifically forms missing for/id bindings on labels/inputs, and icon-only buttons missing aria-label and using unhidden decorative icons. This breaks navigation for visually impaired users.
**Action:** Always bind labels to inputs with matching for and id attributes, and use aria-label alongside aria-hidden='true' for decorative icons inside icon-only interactive elements.
