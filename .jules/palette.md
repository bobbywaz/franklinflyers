## 2024-05-18 - Tailwind Focus Resets on Checkboxes
**Learning:** Tailwind CSS form resets often remove default focus styles from elements like checkboxes (`focus:ring-0`), making them completely invisible to keyboard users and violating accessibility guidelines.
**Action:** When using Tailwind CSS, always explicitly add focus-visible styles (e.g., `focus:ring-2 focus:ring-blue-500`) to form controls to ensure keyboard navigation remains accessible.
