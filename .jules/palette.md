## 2024-11-04 - Improve Checkbox Accessibility
**Learning:** Tailwind CSS resets often remove default focus styles from form inputs. In `templates/index.html`, the `.store-checkbox` class explicitly sets `focus:ring-0 focus:ring-offset-0`, making the checkbox completely invisible when navigating via keyboard (tabbing). This severely hinders keyboard accessibility.
**Action:** Always replace `focus:ring-0` with a visible focus indicator like `focus:ring-2 focus:ring-blue-500` or `focus-visible:ring-2` to ensure interactive elements are accessible to keyboard users.
