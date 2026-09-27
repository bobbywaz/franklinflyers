## 2025-02-23 - Admin Form Accessibility Bindings
**Learning:** Older HTML templates in the project (like `admin_login.html` and `admin.html`) lack proper accessibility associations like `for`/`id` bindings on forms and `aria-label`s on icon-only buttons. Screen readers rely on these for context.
**Action:** When working on UI templates in this project, explicitly verify that all `<label>`s have `for` attributes mapping to `<input>` `id`s, and that all buttons (especially icon-only ones) have descriptive `aria-label`s.
