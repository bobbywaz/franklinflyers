## 2026-05-18 - Improve Keyboard Accessibility of Checkboxes
**Learning:** Tailwind CSS resets like `focus:ring-0` completely remove visual focus indicators, breaking keyboard accessibility (tab navigation) for interactive form elements like checkboxes in `templates/index.html`. Using visible focus rings (e.g., `focus:ring-2 focus:ring-blue-500`) is critical for screen reader users and those navigating without a mouse.
**Action:** Always replace `focus:ring-0` and `focus:outline-none` with visible focus styles like `focus:ring-2` on interactive elements to ensure a11y compliance.
