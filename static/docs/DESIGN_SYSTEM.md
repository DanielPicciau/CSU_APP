# CSU Tracker Design System

## Information Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CSU Tracker App                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   TODAY     │  │   HISTORY   │  │   INSIGHTS  │              │
│  │             │  │             │  │             │              │
│  │ • Daily     │  │ • Calendar  │  │ • UAS7      │              │
│  │   Status    │  │   View      │  │   Trends    │              │
│  │ • Quick     │  │ • Entry     │  │ • Charts    │              │
│  │   Score     │  │   List      │  │ • Export    │              │
│  │ • Week      │  │ • Filters   │  │   Data      │              │
│  │   Overview  │  │             │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                   │
│  ┌─────────────┐  ┌─────────────────────────────────────────────┐
│  │  SETTINGS   │  │                LOG ENTRY                    │
│  │             │  │                                             │
│  │ • Profile   │  │  • Itch Score (0-3)                        │
│  │ • Notifs    │  │  • Hive Count (0-3)                        │
│  │ • Theme     │  │  • Antihistamine Toggle                    │
│  │ • Data      │  │  • Notes                                   │
│  │ • Help      │  │  • Save/Update                             │
│  └─────────────┘  └─────────────────────────────────────────────┘
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  [Today] [History] [+Log] [Insights] [Settings]   ← Bottom Nav  │
└─────────────────────────────────────────────────────────────────┘
```

## Navigation Structure

| Tab | Route | Purpose |
|-----|-------|---------|
| Today | `/` | Dashboard with daily status and weekly overview |
| History | `/history/` | Past entries with calendar and list views |
| Log (+) | `/log/` | Create or edit daily symptom entries |
| Insights | `/history/?view=insights` | Charts, trends, and UAS7 analysis |
| Settings | `/notifications/settings/` | Preferences, theme, notifications |

---

## Component Library

### 1. Buttons

**Variants:**
- `btn--primary` - Main actions (Save, Submit)
- `btn--secondary` - Secondary actions (Cancel, Back)
- `btn--ghost` - Tertiary/text actions
- `btn--destructive` - Destructive actions (Delete)

**Sizes:**
- `btn--sm` - Small (36px height)
- Default - Medium (44px height)
- `btn--lg` - Large (56px height)

**Modifiers:**
- `btn--full` - Full width
- `btn--icon` - Icon-only button

```html
<!-- Primary Button -->
<button class="btn btn--primary">Save Entry</button>

<!-- Secondary with icon -->
<button class="btn btn--secondary">
  <svg>...</svg>
  Cancel
</button>

<!-- Destructive full-width -->
<button class="btn btn--destructive btn--full">Delete Account</button>

<!-- Icon button -->
<button class="btn btn--icon btn--ghost" aria-label="Close">
  <svg>...</svg>
</button>
```

---

### 2. Cards

**Variants:**
- Default - Standard card
- `card--elevated` - More prominent shadow
- `card--interactive` - Clickable/tappable cards
- `card--score` - Score display card

```html
<!-- Standard Card -->
<div class="card">
  <div class="card__header">
    <h3 class="card__title">Week Overview</h3>
  </div>
  <div class="card__body">
    Content here
  </div>
  <div class="card__footer">
    <button class="btn btn--ghost">View All</button>
  </div>
</div>

<!-- Score Card -->
<div class="card card--score">
  <div class="card__score-value score-bg-3">3</div>
  <h2>Today's Score</h2>
  <p>Itch: 2/3 • Hives: 1/3</p>
</div>
```

---

### 3. Form Inputs

```html
<!-- Text Input -->
<div class="form-group">
  <label class="form-label" for="email">Email</label>
  <input type="email" id="email" class="form-input" placeholder="you@example.com">
  <p class="form-helper">We'll never share your email.</p>
</div>

<!-- Textarea -->
<div class="form-group">
  <label class="form-label" for="notes">Notes</label>
  <textarea id="notes" class="form-input form-textarea" placeholder="How are you feeling?"></textarea>
</div>

<!-- Error State -->
<div class="form-group">
  <label class="form-label" for="password">Password</label>
  <input type="password" id="password" class="form-input form-input--error" aria-invalid="true">
  <p class="form-error">Password must be at least 8 characters.</p>
</div>
```

---

### 4. Radio Cards

Large, touch-friendly selection cards for symptom scoring:

```html
<div class="form-group">
  <label class="form-label form-label--lg">Itch Intensity</label>
  <div class="radio-group">
    <label class="radio-card">
      <input type="radio" name="itch" value="0" class="radio-card__input">
      <span class="radio-card__indicator"></span>
      <div class="radio-card__content">
        <div class="radio-card__title">0 - None</div>
        <div class="radio-card__description">No itching at all</div>
      </div>
    </label>
    <label class="radio-card">
      <input type="radio" name="itch" value="1" class="radio-card__input">
      <span class="radio-card__indicator"></span>
      <div class="radio-card__content">
        <div class="radio-card__title">1 - Mild</div>
        <div class="radio-card__description">Present but not annoying</div>
      </div>
    </label>
    <!-- ... more options -->
  </div>
</div>
```

---

### 5. Toggle / Switch

iOS-style toggle switch:

```html
<label class="toggle">
  <input type="checkbox" class="toggle__input" id="notifications">
  <span class="toggle__track">
    <span class="toggle__thumb"></span>
  </span>
  <span class="toggle__label">Enable Notifications</span>
</label>
```

---

### 6. Modal / Dialog

Centered modal for confirmations and forms:

```html
<!-- Backdrop -->
<div id="delete-modal-backdrop" class="modal-backdrop"></div>

<!-- Modal -->
<div id="delete-modal" class="modal" role="dialog" aria-labelledby="modal-title" aria-modal="true">
  <div class="modal__header">
    <h2 id="modal-title" class="modal__title">Delete Entry?</h2>
    <button class="modal__close" onclick="CSU.Modal.close('delete-modal')" aria-label="Close">
      <svg>...</svg>
    </button>
  </div>
  <div class="modal__body">
    <p>This action cannot be undone.</p>
  </div>
  <div class="modal__footer">
    <button class="btn btn--secondary" onclick="CSU.Modal.close('delete-modal')">Cancel</button>
    <button class="btn btn--destructive">Delete</button>
  </div>
</div>

<!-- JavaScript -->
<script>
  CSU.Modal.open('delete-modal');
</script>
```

---

### 7. Bottom Sheet

iOS-style sliding panel from bottom:

```html
<!-- Backdrop -->
<div id="filter-sheet-backdrop" class="bottom-sheet-backdrop"></div>

<!-- Bottom Sheet -->
<div id="filter-sheet" class="bottom-sheet" role="dialog" aria-labelledby="sheet-title">
  <div class="bottom-sheet__handle">
    <div class="bottom-sheet__handle-bar"></div>
  </div>
  <div class="bottom-sheet__header">
    <h2 id="sheet-title" class="bottom-sheet__title">Filter Entries</h2>
  </div>
  <div class="bottom-sheet__body">
    <!-- Filter content -->
  </div>
</div>

<!-- JavaScript -->
<script>
  CSU.BottomSheet.open('filter-sheet');
</script>
```

---

### 8. Toast / Feedback Banner

**Toast Notifications (JavaScript API):**

```javascript
// Success toast
CSU.Toast.success('Entry saved successfully!');

// Error toast
CSU.Toast.error('Failed to save entry. Please try again.');

// Warning toast
CSU.Toast.warning('You haven\'t logged in 3 days.');

// Info toast with title
CSU.Toast.show({
  type: 'info',
  title: 'Reminder',
  message: 'Don\'t forget to log your symptoms today!',
  duration: 5000
});
```

**Inline Feedback Banner (Django messages):**

```html
<div class="feedback-banner feedback-banner--success" role="alert">
  <svg class="feedback-banner__icon">...</svg>
  <span class="feedback-banner__text">Your entry has been saved.</span>
</div>
```

---

## Design Tokens Reference

### Color Palette

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--bg-primary` | #FFFFFF | #0A0A0A | Main background |
| `--bg-secondary` | #FAFAFA | #171717 | Page background |
| `--surface-primary` | #FFFFFF | #171717 | Cards, modals |
| `--text-primary` | #171717 | #FAFAFA | Main text |
| `--text-secondary` | #525252 | #A3A3A3 | Secondary text |
| `--interactive-primary` | #4F46E5 | #4F46E5 | Primary buttons |

### Score Colors

| Score | Color | Token |
|-------|-------|-------|
| 0 | Green (#22C55E) | `--color-score-0` |
| 1 | Light Green (#4ADE80) | `--color-score-1` |
| 2 | Yellow (#FACC15) | `--color-score-2` |
| 3 | Orange (#FB923C) | `--color-score-3` |
| 4 | Dark Orange (#F97316) | `--color-score-4` |
| 5 | Red (#EF4444) | `--color-score-5` |
| 6 | Dark Red (#DC2626) | `--color-score-6` |

### Typography Scale

| Token | Size | Use Case |
|-------|------|----------|
| `--text-xs` | 12px | Labels, captions |
| `--text-sm` | 14px | Helper text |
| `--text-base` | 16px | Body text |
| `--text-lg` | 18px | Section titles |
| `--text-xl` | 20px | Card titles |
| `--text-2xl` | 24px | Page headers |
| `--text-3xl` | 30px | Large numbers |

### Spacing Scale

| Token | Size | Usage |
|-------|------|-------|
| `--space-1` | 4px | Tight spacing |
| `--space-2` | 8px | Between elements |
| `--space-3` | 12px | Small padding |
| `--space-4` | 16px | Standard padding |
| `--space-5` | 20px | Card padding |
| `--space-6` | 24px | Section spacing |
| `--space-8` | 32px | Large spacing |
| `--space-11` | 44px | Touch target size |

---

## Accessibility Guidelines

### WCAG 2.1 AA Compliance

1. **Color Contrast**: All text meets 4.5:1 ratio (or 3:1 for large text)
2. **Focus States**: Visible focus rings on all interactive elements
3. **Touch Targets**: Minimum 44x44px for all tappable elements
4. **ARIA Labels**: All icon-only buttons have labels
5. **Keyboard Navigation**: Full keyboard accessibility
6. **Screen Reader**: Proper heading hierarchy and landmarks

### Implementation Checklist

- [ ] All buttons have visible focus states
- [ ] Form inputs have associated labels
- [ ] Error messages are linked with `aria-describedby`
- [ ] Modals trap focus and are dismissible with Escape
- [ ] Skip link present for keyboard users
- [ ] Color is not the only indicator of state
- [ ] Touch targets are at least 44x44px

---

## Theme Switching

```javascript
// Get current theme
CSU.ThemeManager.getTheme(); // 'light', 'dark', or 'system'

// Set theme
CSU.ThemeManager.setTheme('dark');
CSU.ThemeManager.setTheme('light');
CSU.ThemeManager.setTheme('system'); // Follow OS preference
```

---

## File Structure

```
static/
├── css/
│   ├── design-tokens.css    # Color, typography, spacing tokens
│   └── components.css       # Component styles
├── js/
│   └── components.js        # Interactive component behaviors
└── icons/
    └── ...                  # App icons

templates/
├── base_new.html            # New AppShell layout
├── tracking/
│   ├── home.html
│   ├── log_entry.html
│   └── history.html
└── ...
```

---

## Migration Notes

To migrate from the old base.html to the new design system:

1. Update template to extend `base_new.html`
2. Replace Tailwind classes with design system classes
3. Use semantic component classes (`.btn--primary`, `.card`, etc.)
4. Add proper ARIA labels to interactive elements
5. Test on iOS devices for safe area behavior

Example migration:

```html
<!-- Before (Tailwind) -->
<button class="bg-indigo-600 text-white py-3 px-6 rounded-xl font-semibold">
  Save
</button>

<!-- After (Design System) -->
<button class="btn btn--primary">Save</button>
```
