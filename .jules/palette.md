## $(date +%Y-%m-%d) - Adding ARIA Labels to Missing Icons
**Learning:** Found several icon-only buttons (like `▶` and `🎯`) and visually hidden input fields (like search inputs relying solely on placeholders) that lacked `aria-label`s, which is critical for screen-reader users to understand the component's purpose.
**Action:** Always verify if an interactive element relies purely on visual cues (like emojis, SVG icons, or placeholders) and add an `aria-label` or `aria-labelledby` attribute when no visible text is present.
