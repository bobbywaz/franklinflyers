## 2023-11-02 - Ensure Keyboard Accessibility for Interactive Elements
**Learning:** Found multiple instances where Tailwind reset classes (`focus:outline-none`, `focus:ring-0`) obscure keyboard focus states on interactive elements like buttons, checkboxes, inputs and links, leading to poor keyboard accessibility.
**Action:** Replace `focus:outline-none` and `focus:ring-0` with explicit, visible focus states like `focus:ring-2 focus:ring-blue-500 focus:outline-none` or `focus:ring-2 focus:ring-offset-2` to provide clear keyboard focus indicators across templates.
