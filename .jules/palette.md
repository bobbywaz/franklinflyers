## 2024-05-15 - Focus Visibility
**Learning:** Tailwind CSS reset utilities like `focus:outline-none` and `focus:ring-0` often obscure focus states entirely, severely hurting keyboard accessibility on interactive elements like buttons and checkboxes.
**Action:** Explicitly define focus states using `focus:ring-2` with appropriate colors and offsets (e.g. `focus:ring-offset-2`) for all interactive elements to ensure clear visible focus.
