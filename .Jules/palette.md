## 2024-05-18 - Semantic labels and hidden icons
**Learning:** Using simple unicode emojis as icons can be inaccessible unless they are explicitly hidden from screen readers using `aria-hidden="true"` and a separate `aria-label` is applied to the interactive element.
**Action:** Always wrap visual-only icons in an aria-hidden tag and ensure an aria-label on the interactive container.
