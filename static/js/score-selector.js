/**
 * CSU Tracker - Score Selector JavaScript
 * ========================================
 * Interactive behaviors for premium score selection
 */

(function () {
  'use strict';

  // Score color mapping (0-6 for daily, can extend to 42 for UAS7)
  const SCORE_COLORS = {
    0: '#22C55E',
    1: '#4ADE80',
    2: '#FACC15',
    3: '#FB923C',
    4: '#F97316',
    5: '#EF4444',
    6: '#DC2626'
  };

  const SCORE_DESCRIPTIONS = {
    0: 'No symptoms',
    1: 'Very mild',
    2: 'Mild',
    3: 'Moderate',
    4: 'Moderate-Severe',
    5: 'Severe',
    6: 'Very severe'
  };

  // For UAS7 weekly scores (0-42)
  const UAS7_DESCRIPTIONS = {
    range: [
      { max: 6, label: 'Well controlled', color: '#22C55E' },
      { max: 15, label: 'Mild activity', color: '#4ADE80' },
      { max: 27, label: 'Moderate activity', color: '#FB923C' },
      { max: 42, label: 'Severe activity', color: '#DC2626' }
    ],
    getDescription(score) {
      for (const r of this.range) {
        if (score <= r.max) return r;
      }
      return this.range[this.range.length - 1];
    }
  };

  // ==========================================================================
  // SLIDER SCORE SELECTOR
  // ==========================================================================

  class ScoreSlider {
    constructor(element, options = {}) {
      this.element = element;
      this.options = {
        min: 0,
        max: options.max || 6,
        value: options.value || 0,
        onChange: options.onChange || (() => { }),
        ...options
      };

      this.slider = element.querySelector('.score-selector__slider');
      this.valueDisplay = element.querySelector('.score-selector__value');
      this.descriptionDisplay = element.querySelector('.score-selector__description');
      this.ticks = element.querySelectorAll('.score-selector__tick');

      this.init();
    }

    init() {
      if (!this.slider) return;

      this.slider.min = this.options.min;
      this.slider.max = this.options.max;
      this.slider.value = this.options.value;

      this.slider.addEventListener('input', (e) => this.handleChange(e));
      this.slider.addEventListener('change', (e) => this.handleComplete(e));

      // Keyboard support
      this.slider.addEventListener('keydown', (e) => this.handleKeydown(e));

      this.updateDisplay(this.options.value);
    }

    handleChange(e) {
      const value = parseInt(e.target.value);
      this.updateDisplay(value);
      this.triggerHaptic();
    }

    handleComplete(e) {
      const value = parseInt(e.target.value);
      this.options.onChange(value);
    }

    handleKeydown(e) {
      // Haptic on arrow key press
      if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
        setTimeout(() => this.triggerHaptic(), 50);
      }
    }

    updateDisplay(value) {
      const color = this.getScoreColor(value);

      // Update CSS variable
      this.element.style.setProperty('--score-color', color);

      // Update value display
      if (this.valueDisplay) {
        this.valueDisplay.textContent = value;
      }

      // Update description
      if (this.descriptionDisplay) {
        this.descriptionDisplay.textContent = this.getScoreDescription(value);
      }

      // Update ticks
      this.ticks.forEach((tick, index) => {
        tick.classList.toggle('score-selector__tick--active', index === value);
      });
    }

    getScoreColor(value) {
      if (this.options.max <= 6) {
        return SCORE_COLORS[value] || SCORE_COLORS[6];
      }
      // For UAS7 (0-42)
      const info = UAS7_DESCRIPTIONS.getDescription(value);
      return info.color;
    }

    getScoreDescription(value) {
      if (this.options.max <= 6) {
        return SCORE_DESCRIPTIONS[value] || '';
      }
      // For UAS7
      const info = UAS7_DESCRIPTIONS.getDescription(value);
      return info.label;
    }

    triggerHaptic() {
      if ('vibrate' in navigator) {
        navigator.vibrate(5);
      }
    }

    setValue(value) {
      this.slider.value = value;
      this.updateDisplay(value);
    }

    getValue() {
      return parseInt(this.slider.value);
    }
  }

  // ==========================================================================
  // SEGMENTED SCORE SELECTOR
  // ==========================================================================

  class ScoreSegmented {
    constructor(element, options = {}) {
      this.element = element;
      this.options = {
        value: options.value || 0,
        onChange: options.onChange || (() => { }),
        ...options
      };

      this.inputs = element.querySelectorAll('.score-segmented__input');
      this.valueDisplay = element.querySelector('.score-segmented__value');
      this.labelDisplay = element.querySelector('.score-segmented__label');

      this.init();
    }

    init() {
      this.inputs.forEach(input => {
        input.addEventListener('change', (e) => this.handleChange(e));
      });

      // Set initial value
      const initialInput = this.element.querySelector(`input[value="${this.options.value}"]`);
      if (initialInput) {
        initialInput.checked = true;
        this.updateDisplay(this.options.value);
      }
    }

    handleChange(e) {
      const value = parseInt(e.target.value);
      this.updateDisplay(value);
      this.triggerHaptic();
      this.options.onChange(value);
    }

    updateDisplay(value) {
      const color = SCORE_COLORS[value] || SCORE_COLORS[6];
      this.element.style.setProperty('--score-color', color);

      if (this.valueDisplay) {
        this.valueDisplay.textContent = value;
      }

      if (this.labelDisplay) {
        this.labelDisplay.textContent = SCORE_DESCRIPTIONS[value] || '';
      }

      // Update button colors
      this.inputs.forEach(input => {
        const btn = input.nextElementSibling;
        if (btn && input.checked) {
          btn.style.setProperty('--score-color', color);
        }
      });
    }

    triggerHaptic() {
      if ('vibrate' in navigator) {
        navigator.vibrate(10);
      }
    }

    setValue(value) {
      const input = this.element.querySelector(`input[value="${value}"]`);
      if (input) {
        input.checked = true;
        this.updateDisplay(value);
      }
    }

    getValue() {
      const checked = this.element.querySelector('input:checked');
      return checked ? parseInt(checked.value) : 0;
    }
  }

  // ==========================================================================
  // DIAL SCORE SELECTOR
  // ==========================================================================

  class ScoreDial {
    constructor(element, options = {}) {
      this.element = element;
      this.options = {
        min: 0,
        max: options.max || 6,
        value: options.value || 0,
        onChange: options.onChange || (() => { }),
        ...options
      };

      this.valueDisplay = element.querySelector('.score-dial__value');
      this.descriptionDisplay = element.querySelector('.score-dial__description');
      this.progressPath = element.querySelector('.score-dial__progress');
      this.touchArea = element.querySelector('.score-dial__touch-area');
      this.decrementBtn = element.querySelector('[data-dial-decrement]');
      this.incrementBtn = element.querySelector('[data-dial-increment]');

      this.value = this.options.value;
      this.isDragging = false;

      this.init();
    }

    init() {
      // Button controls
      if (this.decrementBtn) {
        this.decrementBtn.addEventListener('click', () => this.decrement());
      }
      if (this.incrementBtn) {
        this.incrementBtn.addEventListener('click', () => this.increment());
      }

      // Touch/drag on dial
      if (this.touchArea) {
        this.touchArea.addEventListener('touchstart', (e) => this.handleTouchStart(e));
        this.touchArea.addEventListener('touchmove', (e) => this.handleTouchMove(e));
        this.touchArea.addEventListener('touchend', () => this.handleTouchEnd());
        this.touchArea.addEventListener('click', (e) => this.handleClick(e));
      }

      // Keyboard support
      this.element.setAttribute('tabindex', '0');
      this.element.setAttribute('role', 'slider');
      this.element.setAttribute('aria-valuemin', this.options.min);
      this.element.setAttribute('aria-valuemax', this.options.max);
      this.element.addEventListener('keydown', (e) => this.handleKeydown(e));

      this.updateDisplay();
    }

    handleTouchStart(e) {
      this.isDragging = true;
      this.updateFromTouch(e.touches[0]);
    }

    handleTouchMove(e) {
      if (!this.isDragging) return;
      e.preventDefault();
      this.updateFromTouch(e.touches[0]);
    }

    handleTouchEnd() {
      if (this.isDragging) {
        this.isDragging = false;
        this.options.onChange(this.value);
      }
    }

    handleClick(e) {
      this.updateFromTouch(e);
      this.options.onChange(this.value);
    }

    updateFromTouch(touch) {
      const rect = this.touchArea.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      let angle = Math.atan2(touch.clientY - centerY, touch.clientX - centerX);
      angle = angle * (180 / Math.PI) + 90; // Rotate to start from top
      if (angle < 0) angle += 360;

      // Map angle to value (270 degrees = full scale)
      const maxAngle = 270;
      const startAngle = 135; // Start from bottom-left

      let normalizedAngle = angle - startAngle;
      if (normalizedAngle < 0) normalizedAngle += 360;

      const ratio = Math.min(Math.max(normalizedAngle / maxAngle, 0), 1);
      const newValue = Math.round(ratio * this.options.max);

      if (newValue !== this.value) {
        this.value = newValue;
        this.updateDisplay();
        this.triggerHaptic();
      }
    }

    handleKeydown(e) {
      switch (e.key) {
        case 'ArrowUp':
        case 'ArrowRight':
          e.preventDefault();
          this.increment();
          break;
        case 'ArrowDown':
        case 'ArrowLeft':
          e.preventDefault();
          this.decrement();
          break;
        case 'Home':
          e.preventDefault();
          this.setValue(this.options.min);
          this.options.onChange(this.value);
          break;
        case 'End':
          e.preventDefault();
          this.setValue(this.options.max);
          this.options.onChange(this.value);
          break;
      }
    }

    increment() {
      if (this.value < this.options.max) {
        this.value++;
        this.updateDisplay();
        this.triggerHaptic();
        this.options.onChange(this.value);
      }
    }

    decrement() {
      if (this.value > this.options.min) {
        this.value--;
        this.updateDisplay();
        this.triggerHaptic();
        this.options.onChange(this.value);
      }
    }

    updateDisplay() {
      const color = this.getScoreColor(this.value);
      this.element.style.setProperty('--score-color', color);

      // Update ARIA
      this.element.setAttribute('aria-valuenow', this.value);
      this.element.setAttribute('aria-valuetext', `${this.value} - ${this.getScoreDescription(this.value)}`);

      // Update value
      if (this.valueDisplay) {
        this.valueDisplay.textContent = this.value;
      }

      // Update description
      if (this.descriptionDisplay) {
        this.descriptionDisplay.textContent = this.getScoreDescription(this.value);
      }

      // Update progress arc
      if (this.progressPath) {
        const circumference = 2 * Math.PI * 120; // radius = 120
        const arcLength = 0.75; // 270 degrees / 360
        const progress = this.value / this.options.max;
        const dashLength = circumference * arcLength * progress;
        const gapLength = circumference - dashLength;
        this.progressPath.style.strokeDasharray = `${dashLength} ${gapLength}`;
      }

      // Update button states
      if (this.decrementBtn) {
        this.decrementBtn.disabled = this.value <= this.options.min;
      }
      if (this.incrementBtn) {
        this.incrementBtn.disabled = this.value >= this.options.max;
      }
    }

    getScoreColor(value) {
      if (this.options.max <= 6) {
        return SCORE_COLORS[value] || SCORE_COLORS[6];
      }
      const info = UAS7_DESCRIPTIONS.getDescription(value);
      return info.color;
    }

    getScoreDescription(value) {
      if (this.options.max <= 6) {
        return SCORE_DESCRIPTIONS[value] || '';
      }
      const info = UAS7_DESCRIPTIONS.getDescription(value);
      return info.label;
    }

    triggerHaptic() {
      if ('vibrate' in navigator) {
        navigator.vibrate(8);
      }
    }

    setValue(value) {
      this.value = Math.max(this.options.min, Math.min(this.options.max, value));
      this.updateDisplay();
    }

    getValue() {
      return this.value;
    }
  }

  // ==========================================================================
  // SEVERITY SELECTOR
  // ==========================================================================

  class SeveritySelector {
    constructor(element, options = {}) {
      this.element = element;
      this.options = {
        name: options.name || 'severity',
        value: options.value,
        onChange: options.onChange || (() => { }),
        ...options
      };

      this.cards = element.querySelectorAll('.severity-card');
      this.inputs = element.querySelectorAll('.severity-card__input');

      this.init();
    }

    init() {
      this.inputs.forEach(input => {
        input.addEventListener('change', (e) => this.handleChange(e));
      });

      // Set initial value
      if (this.options.value !== undefined) {
        const input = this.element.querySelector(`input[value="${this.options.value}"]`);
        if (input) {
          input.checked = true;
          this.updateUI();
        }
      }
    }

    handleChange(e) {
      this.updateUI();
      this.triggerHaptic();
      this.options.onChange(parseInt(e.target.value));
    }

    updateUI() {
      this.cards.forEach(card => {
        const input = card.querySelector('.severity-card__input');
        card.classList.toggle('severity-card--selected', input.checked);
      });
    }

    triggerHaptic() {
      if ('vibrate' in navigator) {
        navigator.vibrate(10);
      }
    }

    setValue(value) {
      const input = this.element.querySelector(`input[value="${value}"]`);
      if (input) {
        input.checked = true;
        this.updateUI();
      }
    }

    getValue() {
      const checked = this.element.querySelector('input:checked');
      return checked ? parseInt(checked.value) : null;
    }
  }

  // ==========================================================================
  // UNSAVED CHANGES WARNING
  // ==========================================================================

  class UnsavedChangesTracker {
    constructor(form, options = {}) {
      this.form = form;
      this.options = {
        message: 'You have unsaved changes. Are you sure you want to leave?',
        ...options
      };

      this.initialState = this.getFormState();
      this.hasChanges = false;

      this.init();
    }

    init() {
      // Track changes
      this.form.addEventListener('input', () => this.checkForChanges());
      this.form.addEventListener('change', () => this.checkForChanges());

      // Warn on navigation
      window.addEventListener('beforeunload', (e) => this.handleBeforeUnload(e));

      // Track form submission
      this.form.addEventListener('submit', () => {
        this.hasChanges = false;
      });
    }

    getFormState() {
      const formData = new FormData(this.form);
      const state = {};
      for (const [key, value] of formData.entries()) {
        state[key] = value;
      }
      return JSON.stringify(state);
    }

    checkForChanges() {
      const currentState = this.getFormState();
      this.hasChanges = currentState !== this.initialState;
      this.updateUI();
    }

    updateUI() {
      // Add visual indicator
      const indicator = this.form.querySelector('.unsaved-indicator');
      if (indicator) {
        indicator.classList.toggle('unsaved-indicator--visible', this.hasChanges);
      }

      // Update save button
      const saveBtn = this.form.querySelector('[type="submit"]');
      if (saveBtn && this.hasChanges) {
        saveBtn.classList.add('btn--has-changes');
      } else if (saveBtn) {
        saveBtn.classList.remove('btn--has-changes');
      }
    }

    handleBeforeUnload(e) {
      if (this.hasChanges) {
        e.preventDefault();
        e.returnValue = this.options.message;
        return this.options.message;
      }
    }

    reset() {
      this.initialState = this.getFormState();
      this.hasChanges = false;
      this.updateUI();
    }

    hasUnsavedChanges() {
      return this.hasChanges;
    }
  }

  // ==========================================================================
  // TODAY API CLIENT
  // ==========================================================================

  class TodayAPI {
    constructor(options = {}) {
      this.baseUrl = options.baseUrl || '/api';
      this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    async getToday() {
      const response = await fetch(`${this.baseUrl}/tracking/today/`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'same-origin',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch today\'s entry');
      }

      return response.json();
    }

    async saveToday(data) {
      const response = await fetch(`${this.baseUrl}/tracking/today/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-CSRFToken': this.csrfToken,
        },
        credentials: 'same-origin',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save entry');
      }

      return response.json();
    }

    async getEntry(date) {
      const response = await fetch(`${this.baseUrl}/tracking/entries/${date}/`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'same-origin',
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error('Failed to fetch entry');
      }

      return response.json();
    }
  }

  // ==========================================================================
  // AUTO-INITIALIZATION
  // ==========================================================================

  function initScoreSelectors() {
    // Initialize sliders
    document.querySelectorAll('[data-score-slider]').forEach(el => {
      const options = {
        max: parseInt(el.dataset.max) || 6,
        value: parseInt(el.dataset.value) || 0,
        onChange: (value) => {
          el.dispatchEvent(new CustomEvent('score-change', { detail: { value } }));
        }
      };
      el._scoreSlider = new ScoreSlider(el, options);
    });

    // Initialize segmented
    document.querySelectorAll('[data-score-segmented]').forEach(el => {
      const options = {
        value: parseInt(el.dataset.value) || 0,
        onChange: (value) => {
          el.dispatchEvent(new CustomEvent('score-change', { detail: { value } }));
        }
      };
      el._scoreSegmented = new ScoreSegmented(el, options);
    });

    // Initialize dials
    document.querySelectorAll('[data-score-dial]').forEach(el => {
      const options = {
        max: parseInt(el.dataset.max) || 6,
        value: parseInt(el.dataset.value) || 0,
        onChange: (value) => {
          el.dispatchEvent(new CustomEvent('score-change', { detail: { value } }));
        }
      };
      el._scoreDial = new ScoreDial(el, options);
    });

    // Initialize severity selectors
    document.querySelectorAll('[data-severity-selector]').forEach(el => {
      const options = {
        name: el.dataset.name,
        value: el.dataset.value !== undefined ? parseInt(el.dataset.value) : undefined,
        onChange: (value) => {
          el.dispatchEvent(new CustomEvent('severity-change', { detail: { value } }));
        }
      };
      el._severitySelector = new SeveritySelector(el, options);
    });

    // Initialize unsaved changes tracking
    document.querySelectorAll('[data-track-changes]').forEach(form => {
      form._unsavedChanges = new UnsavedChangesTracker(form);
    });
  }

  // Expose to global scope
  window.CSU = window.CSU || {};
  Object.assign(window.CSU, {
    ScoreSlider,
    ScoreSegmented,
    ScoreDial,
    SeveritySelector,
    UnsavedChangesTracker,
    TodayAPI,
    SCORE_COLORS,
    SCORE_DESCRIPTIONS,
    initScoreSelectors
  });

  // Auto-init on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initScoreSelectors);
  } else {
    initScoreSelectors();
  }

})();
