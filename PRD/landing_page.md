# FraudGen Landing Page — Full Component Specification

> **Stack**: React + TypeScript, ShadCN/UI, Tailwind CSS, Framer Motion  
> **Color Palette**: Background `#1D1D1D`, Text white `#FFFFFF` & black `#000000`, Red `#994B4B`, Blue `#44578C`  
> **Typography**: Serif display font (e.g. Playfair Display or similar elegant serif) for headings. Clean sans-serif (e.g. DM Sans or similar) for body/nav text.

---

## 1. Navbar

**Component**: `<Navbar />`

- **Layout**: Fixed top, full-width, horizontal flex row.
- **Left**: Logo text "FraudGen" in serif font, white, regular weight.
- **Right**: Nav links — "About", "Platform", "Solutions", "Company" — evenly spaced, white sans-serif text, subtle opacity hover effect (0.6 → 1.0 on hover).
- **Background**: Transparent, blending into the hero section. No border or shadow.
- **Z-index**: Highest layer so it floats above all scroll content.

---

## 2. Hero Section

**Component**: `<HeroSection />`

### Layout
- Full viewport height (`100vh`), centered content.
- Heading: Large serif text, white — "Empowering you with Ultimate Cybersecurity Solutions" — centered, max-width ~900px.
- CTA button: "See it run" — white/light background, dark text, large pill/rounded-rectangle shape, centered below heading.

### Animations & Effects
- **Gradient noisy background**: The entire hero has a dark noisy/grain texture overlay. Beneath it, a radial gradient (soft purple/violet tones blending into the `#1D1D1D` background) **follows the mouse cursor** in real-time. Use `onMouseMove` to track cursor position and update a CSS radial-gradient origin. The gradient should be subtle — like a soft spotlight trailing the pointer.
- **"See it run" button hover**: On hover, a circular gradient glow appears around the button. This is a radial gradient circle (white/light with soft edges) that fades in on hover and follows the cursor position relative to the button. Use Framer Motion for smooth opacity transitions.
- Below the hero text/button area, the bottom portion of the hero fades into a series of **dark vertical bars/columns** with a faint purple gradient wash — a decorative abstract pattern that gives depth. These are purely decorative CSS elements (repeating vertical strips with varying opacity and a purple-to-dark gradient).

---

## 3. Problem Section — "Fraud detection has a data problem."

**Component**: `<ProblemSection />`

### Layout
- Section heading: Large serif text, white, left-aligned — "Fraud detection has a data problem."
- Below heading, left-aligned: A pill-shaped navigation control with `<` and `>` arrows (white outline on dark background) for cycling through card sets (carousel-style pagination).
- **3 cards** in a horizontal row, evenly spaced.

### Card Design
- Each card: Dark background (`#1D1D1D` or slightly lighter `#2A2A2A`), thin white/light border with a subtle **gradient border effect** (use `border-image` or a wrapper with gradient background + inner dark background to create gradient outlines).
- **Card top half**: Contains a 3D-style abstract illustration (purple/blue/pink glassmorphic geometric shapes). Since we can't generate images, use placeholder `<div>` areas styled with CSS gradients, `backdrop-filter: blur`, and layered shapes to approximate the glassmorphic 3D look — or use placeholder image slots with a comment indicating where to insert the actual assets.
- **Card bottom half**: Bold white sans-serif title + light gray body text below.
- Card titles: "Few Fraud Transactions", "Mule Cases", "Unknown New Variants".
- Card body: Placeholder descriptive text (replace lorem ipsum with real copy).
- **Hover effect**: On hover, the gradient border brightens/shifts color, and the card receives a subtle color-tinted glow (box-shadow with low opacity purple/blue).

### Scroll Animation
- When the user scrolls to this section, the **left and right cards start slightly lower** (translateY offset ~30–50px) and the **middle card starts slightly higher** (translateY offset ~-30px). As the section enters full view, all three cards **converge to the same vertical alignment** with a smooth ease-out transition. Use Framer Motion's `useInView` or scroll-triggered variants with `whileInView`.

---

## 4. Solution Section — Red Team / Blue Team

**Component**: `<SolutionSection />`

### Layout
- Two overlapping cards, positioned with CSS — **not** centered, but offset from the edges of the viewport.
- **Red Team card**: Positioned **top-left** area (with margin from the page edge). Background `#994B4B` with a slightly darker or lighter border. Contains:
  - A hacker/hooded figure icon (use an SVG icon or Lucide icon placeholder) centered at top.
  - Title: "Red Team" in large serif font, white.
  - Bullet points in white sans-serif:
    - "AI agents that think like fraudsters"
    - "Explore the full variant space at scale"
    - "Run proactively before real attacks"
- **Blue Team card**: Positioned **bottom-right** area (with margin from the page edge). Background `#44578C` with a slightly darker or lighter border. Contains:
  - A detective/fedora figure icon (use an SVG icon or Lucide icon placeholder) centered at top.
  - Title: "Blue Team" in large serif font, white.
  - Bullet points in white sans-serif:
    - "Your existing fraud detection pipeline"
    - "Retrains on synthetic data to close gaps"
    - "Deploys hardened models with new coverage"
- The two cards **overlap** in the center — Red card is partially behind/above Blue card by default (using `z-index`).

### Hover / Card Shuffle Animation
- **Default state**: Red card is in front (higher z-index), Blue card is behind and offset to the bottom-right.
- **On Blue card hover**: Trigger a **card shuffle animation**:
  1. Red card translates slightly up-left and its z-index drops (moves to the back). Apply a subtle scale-down (0.95) and slight rotation (-2deg).
  2. Blue card translates slightly forward/up and its z-index rises (moves to the front). Apply a slight scale-up (1.02) and counter-rotation.
  3. The transition should feel like physically shuffling two stacked cards — one slides back while the other slides forward. Use Framer Motion `layout` animations or explicit `animate` variants with ~400ms spring transitions.
- **On hover out**: Cards return to default positions smoothly.

---

## 5. MVP Section — "Introducing the Admin Console"

**Component**: `<MVPSection />`

### Layout
- **Top-left**: Heading text — "Introducing the Admin Console" — in serif font, white, with a subtle blue underline decoration.
- **Center**: A 3D-styled envelope graphic. This can be built with CSS/SVG — a rectangle with a triangular flap on top, styled with gradients (dark purple/gray tones matching the site palette), subtle shadows, and a slight perspective transform to give it depth.
- **Bottom-right**: Text — "Built for Fraud Analysts" — in serif font, white.

### Scroll Animation — Envelope Opens
- As the user scrolls through this section, the **envelope flap animates open**. Use `rotateX` on the triangular flap element:
  - Start: flap is closed (rotateX(0deg), flush with envelope body).
  - On scroll progress (use Framer Motion `useScroll` + `useTransform`): flap rotates backward (rotateX up to ~160deg), revealing the inside of the envelope.
  - Apply `transform-origin: top center` on the flap so it hinges from the top edge.
  - The envelope interior can have a slightly lighter shade to suggest depth.

---

## 6. Envelope Detail / Admin Console Preview

**Component**: `<EnvelopeDetail />`

### Layout
- This is the content "inside" the envelope — revealed after or during the envelope open animation. It appears as a light/white card or panel.
- **Background**: Light gray/white (`#F0F0F0` or similar) with rounded corners and a dark outer border.
- **Top-left**: A dark pill button — "See More Details" — with white text.
- **Bottom-left**: Heading — "Admin observability and monitoring" — in large serif font, black, with a blue underline.
- **Right side**: Two numbered feature callouts:
  - "01." (large serif, black) + "Input & Configure" (serif, slightly smaller)
  - "02." (large serif, black) + "Watch agents live" (serif, slightly smaller)

### Animation
- This panel slides up or fades in from the envelope as the scroll-based envelope open animation completes. Use Framer Motion `useScroll` progress to tie the panel's opacity and translateY to the scroll position.

---

## 7. Agent Stack Section

**Component**: `<AgentStackSection />`

### Layout
- **Background**: `#1D1D1D`
- **Heading**: "Agent Stack" — large serif, white, centered.
- Below: A **7-row, single-column table/list** with rounded container corners. Each row is a horizontal cell with:
  - **Title**: Bold sans-serif, black (since cells have a light background).
  - **Subtitle**: Regular weight, dark gray — descriptive text for each agent.
- Cell backgrounds: Light gray/white (`#F0F0F0`), separated by thin borders or gaps.
- The 7 agents (top to bottom):
  1. **Orchestrator** — "Coordinates the full generation pipeline end-to-end"
  2. **Persona Generator** — "Creates diverse criminal profiles with realistic attributes"
  3. **Coverage Matrix Manager** — "Tracks fraud typology coverage and identifies gaps"
  4. **Fraud Network Constructor** — "Builds interconnected transaction networks"
  5. **Schema Validator** — "Ensures generated data conforms to required formats"
  6. **Critic Agent** — "Reviews and scores synthetic data for realism"
  7. **Data Handler** — "Manages output formatting, batching, and export"

### Hover Effect
- **On cell hover**: The hovered cell **darkens** — apply a background color transition to a darker shade (e.g., `#D0D0D0` or `#C0C0C0`). Transition duration ~200ms ease. Optionally add a subtle inset shadow on hover for a pressed/depth effect.

---

## 8. Data Pipeline Section

**Component**: `<DataPipelineSection />`

### Layout
- **Background**: `#1D1D1D`
- **Heading**: "Data Pipeline" — large serif, white, centered at top.
- Below: A flowchart of 8 rounded-pill nodes connected by lines, arranged in 4 rows:
  - **Row 1** (1 node, centered): `Describe`
  - **Row 2** (3 nodes, horizontal): `Decompose` — `Seed` — `Generate`
  - **Row 3** (3 nodes, horizontal): `Revise` — `Score` — `Validate`
  - **Row 4** (1 node, centered): `Export`
- Connecting lines run vertically from Row 1 → Row 2 (branching to 3), horizontally between nodes in each row, vertically from Row 2 → Row 3 (connected), and vertically from Row 3 → Row 4 (converging to 1).
- Node styling: Light gray/white background pills, dark text, with **drop shadows** — `box-shadow: 10px 10px 50px rgba(0,0,0,0.5)` (10x horizontal, 10y vertical, 50px blur).
- Lines: Thin white or light gray, solid, connecting the nodes.

### Animations
- **Dot-following-path animation**: An animated dot (small glowing circle, white or accent-colored) travels along the connecting lines from `Describe` → `Decompose` → `Seed` → `Generate` → `Revise` → `Score` → `Validate` → `Export`. Use SVG `<path>` elements for the lines and animate a circle along them with `offset-path` / `offset-distance`, or use Framer Motion's path animation. The dot should loop continuously with a moderate speed (~4–6 seconds per full cycle).
- **Export splash effect**: When the user scrolls to the point where `Export` is visible, trigger a one-time "splash" or "burst" animation on the `Export` node — a radial burst of particles or expanding rings that quickly dissipate. This can be done with multiple small circles scaling outward and fading, or a pulsing ring animation. Use Framer Motion `whileInView` with `once: true`.
- Below the flowchart: A **large database icon** (SVG — classic cylinder/barrel shape) centered, with the text **"Dataset ready for ML training"** in large serif font, white, beneath it. The splash effect from `Export` visually connects/transitions into this database icon area.

---

## 9. Footer

**Component**: `<Footer />`

### Layout
- **Background**: `#1D1D1D` or pure black `#000000`.
- Four columns, left to right:
  1. **SITEMAP**: "Home" (underlined/active), "About", "Platform", "Solutions", "Company" — white/gray text, stacked vertically.
  2. **COMPANY**: "Licensign" [sic — match original], "Terms & Conditions", "Privacy", "Policy" — gray text, stacked.
  3. **CONTACT**: "FAQ", "Support" — gray text, stacked.
  4. **NEWSLETTER**: Tagline text — "You read this far, mightas well sign up." [match original copy]. Below: two inline text inputs ("First name", email field showing placeholder "rochmad.k") + a dark pill "Sign up" button to the right.
- Column headers ("SITEMAP", "COMPANY", etc.) in small uppercase gray text, with spacing below.
- Input fields: Underline-style (no full border, just a bottom border), white text on dark background.

---

## Global Notes

- **Scroll behavior**: Smooth scrolling between sections. Each section is full-width and has generous vertical padding.
- **Noise/grain overlay**: Consider a global subtle noise texture overlay (CSS `background-image` with a tiny repeating noise PNG or SVG filter) at very low opacity (~0.03–0.05) across the entire page for texture.
- **Font loading**: Import serif display font (e.g. Playfair Display) and sans-serif body font via Google Fonts or local files.
- **Responsive**: All sections should adapt to mobile. Cards stack vertically, Red/Blue team cards stack instead of overlap, envelope section simplifies, etc.
- **Framer Motion usage**: Use `motion` components throughout. Key hooks: `useScroll`, `useTransform`, `useInView`, `useMotionValue`. Prefer spring animations for card movements, tween for scroll-linked transforms.
- **ShadCN components**: Use `Button`, `Input`, `Card` from ShadCN where applicable, customized with Tailwind overrides to match the dark theme and brand colors.