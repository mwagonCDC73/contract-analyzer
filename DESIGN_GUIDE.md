# California Drywall - Design Guide

## Color Scheme

The application color scheme matches the California Drywall website (www.caldrywall.com) for brand consistency.

### Primary Colors

```css
--cd-black: #000000;          /* Primary brand color - headers, buttons */
--cd-dark-gray: #32373c;      /* Secondary buttons, text */
--cd-light-gray: #abb8c3;     /* Accents, borders, secondary text */
--cd-white: #ffffff;          /* Backgrounds, contrast text */
--cd-bg-light: #f5f5f5;       /* Light backgrounds, cards */
```

### Color Usage

#### Headers & Primary Elements
- **Background**: Linear gradient from `#000000` to `#32373c`
- **Text**: White (`#ffffff`)
- **Accent border**: `#abb8c3`

#### Buttons
- **Primary Button**: Black (`#000000`) background with light gray (`#abb8c3`) border
- **Secondary Button**: Dark gray (`#32373c`) background
- **Hover State**: Swap colors and add border

#### Cards
- **Background**: White (`#ffffff`)
- **Border**: Light gray (`#e5e7eb`) default, `#abb8c3` on hover
- **Shadow**: Subtle black shadow (`rgba(0,0,0,0.08)`)

#### Role Badges
- **Executive**: Black background (`#000000`), white text, light gray border
- **Admin**: Black background with light gray text (`#abb8c3`), bordered
- **Project Manager**: Dark gray background (`#32373c`), white text

#### Text Colors
- **Headings**: Black (`#000000`)
- **Body Text**: Dark gray (`#32373c`)
- **Secondary Text**: Light gray (`#abb8c3`)

### Branding Philosophy

California Drywall uses a minimalist, professional color palette emphasizing:
- **Trust & Stability**: Black and gray tones
- **Professionalism**: Clean, high-contrast design
- **Heritage**: Classic colors reflecting "Building Excellence Since 1946"

### Design Principles

1. **High Contrast**: Black/white combinations for readability
2. **Subtle Accents**: Light gray for borders and secondary elements
3. **Consistent Spacing**: Generous padding and margins
4. **Professional Typography**: Sans-serif, bold headings
5. **Smooth Interactions**: Transitions on hover states

### Implementation Files

- **Global Theme**: `.streamlit/config.toml`
- **Home Page**: Custom CSS in `Home.py`
- **Individual Pages**: Inherit global theme

### Accessibility

The high-contrast black and white color scheme ensures:
- WCAG AA compliance for text contrast
- Clear visual hierarchy
- Readable for color-blind users
- Professional appearance across all screens

---

© 2025 California Drywall Co.
