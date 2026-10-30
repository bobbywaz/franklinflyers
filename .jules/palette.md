## 2024-10-30 - Accessible Focus States on Tailwind Reset Components
**Learning:** Tailwind CSS resets on interactive elements (e.g. `focus:outline-none`, `focus:ring-0`) often obscure focus states entirely, causing poor keyboard navigation accessibility.
**Action:** Next time, avoid default resets on checkboxes and buttons or explicitly implement accessible visible focus states using classes like `focus-visible:ring-2 focus-visible:ring-blue-400 rounded` to ensure keyboard operability.
