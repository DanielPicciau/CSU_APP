/**
 * CSU Tracker Design System - JavaScript Components
 * ==================================================
 * Interactive component behaviors for iOS-optimized experience
 */

(function() {
  'use strict';

  // ==========================================================================
  // THEME MANAGEMENT
  // Light/Dark/System theme switching with persistence
  // ==========================================================================

  const ThemeManager = {
    STORAGE_KEY: 'csu-theme',
    
    init() {
      const savedTheme = localStorage.getItem(this.STORAGE_KEY);
      if (savedTheme) {
        this.setTheme(savedTheme);
      }
      
      // Listen for system preference changes
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (!localStorage.getItem(this.STORAGE_KEY)) {
          this.updateMetaTheme();
        }
      });
      
      this.updateMetaTheme();
    },
    
    setTheme(theme) {
      if (theme === 'system') {
        document.documentElement.removeAttribute('data-theme');
        localStorage.removeItem(this.STORAGE_KEY);
      } else {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(this.STORAGE_KEY, theme);
      }
      this.updateMetaTheme();
    },
    
    getTheme() {
      return localStorage.getItem(this.STORAGE_KEY) || 'system';
    },
    
    updateMetaTheme() {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark' ||
        (!document.documentElement.hasAttribute('data-theme') && 
         window.matchMedia('(prefers-color-scheme: dark)').matches);
      
      const metaTheme = document.querySelector('meta[name="theme-color"]');
      if (metaTheme) {
        metaTheme.setAttribute('content', isDark ? '#0A0A0A' : '#FAFAFA');
      }
    }
  };

  // ==========================================================================
  // TOAST NOTIFICATIONS
  // Non-intrusive feedback system
  // ==========================================================================

  const Toast = {
    container: null,
    queue: [],
    
    init() {
      this.container = document.getElementById('toast-container');
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.className = 'toast-container';
        this.container.setAttribute('aria-live', 'polite');
        this.container.setAttribute('aria-atomic', 'true');
        document.body.appendChild(this.container);
      }
    },
    
    show(options = {}) {
      const {
        type = 'info',
        title = '',
        message = '',
        duration = 4000,
        dismissible = true
      } = options;
      
      const toast = document.createElement('div');
      toast.className = `toast toast--${type}`;
      toast.setAttribute('role', 'alert');
      
      const icons = {
        success: '<svg class="toast__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        error: '<svg class="toast__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        warning: '<svg class="toast__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        info: '<svg class="toast__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
      };
      
      toast.innerHTML = `
        ${icons[type] || icons.info}
        <div class="toast__content">
          ${title ? `<div class="toast__title">${title}</div>` : ''}
          ${message ? `<div class="toast__message">${message}</div>` : ''}
        </div>
        ${dismissible ? `
          <button class="toast__dismiss" aria-label="Dismiss notification">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        ` : ''}
      `;
      
      this.container.appendChild(toast);
      
      // Trigger reflow for animation
      toast.offsetHeight;
      toast.classList.add('toast--active');
      
      // Dismiss handler
      const dismiss = () => {
        toast.classList.remove('toast--active');
        setTimeout(() => toast.remove(), 300);
      };
      
      if (dismissible) {
        toast.querySelector('.toast__dismiss').addEventListener('click', dismiss);
      }
      
      if (duration > 0) {
        setTimeout(dismiss, duration);
      }
      
      return { dismiss };
    },
    
    success(message, title = '') {
      return this.show({ type: 'success', title, message });
    },
    
    error(message, title = '') {
      return this.show({ type: 'error', title, message });
    },
    
    warning(message, title = '') {
      return this.show({ type: 'warning', title, message });
    },
    
    info(message, title = '') {
      return this.show({ type: 'info', title, message });
    }
  };

  // ==========================================================================
  // MODAL COMPONENT
  // Accessible modal dialogs
  // ==========================================================================

  const Modal = {
    activeModal: null,
    previousFocus: null,
    
    open(modalId) {
      const modal = document.getElementById(modalId);
      const backdrop = document.getElementById(`${modalId}-backdrop`) || 
                       document.querySelector('.modal-backdrop');
      
      if (!modal) return;
      
      this.previousFocus = document.activeElement;
      this.activeModal = modal;
      
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
      
      // Show modal
      if (backdrop) backdrop.classList.add('modal-backdrop--active');
      modal.classList.add('modal--active');
      
      // Focus management
      const focusable = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length) focusable[0].focus();
      
      // Trap focus
      modal.addEventListener('keydown', this.trapFocus);
      
      // Close on backdrop click
      if (backdrop) {
        backdrop.addEventListener('click', () => this.close(modalId));
      }
      
      // Close on Escape
      document.addEventListener('keydown', this.handleEscape);
    },
    
    close(modalId) {
      const modal = document.getElementById(modalId);
      const backdrop = document.getElementById(`${modalId}-backdrop`) || 
                       document.querySelector('.modal-backdrop');
      
      if (!modal) return;
      
      modal.classList.remove('modal--active');
      if (backdrop) backdrop.classList.remove('modal-backdrop--active');
      
      document.body.style.overflow = '';
      
      // Restore focus
      if (this.previousFocus) {
        this.previousFocus.focus();
      }
      
      // Cleanup listeners
      modal.removeEventListener('keydown', this.trapFocus);
      document.removeEventListener('keydown', this.handleEscape);
      
      this.activeModal = null;
    },
    
    trapFocus(e) {
      if (e.key !== 'Tab') return;
      
      const modal = e.currentTarget;
      const focusable = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    },
    
    handleEscape(e) {
      if (e.key === 'Escape' && Modal.activeModal) {
        Modal.close(Modal.activeModal.id);
      }
    }
  };

  // ==========================================================================
  // BOTTOM SHEET COMPONENT
  // iOS-style sliding panel with gesture support
  // ==========================================================================

  const BottomSheet = {
    activeSheet: null,
    startY: 0,
    currentY: 0,
    isDragging: false,
    
    open(sheetId) {
      const sheet = document.getElementById(sheetId);
      const backdrop = document.getElementById(`${sheetId}-backdrop`) || 
                       document.querySelector('.bottom-sheet-backdrop');
      
      if (!sheet) return;
      
      this.activeSheet = sheet;
      document.body.style.overflow = 'hidden';
      
      if (backdrop) backdrop.classList.add('bottom-sheet-backdrop--active');
      sheet.classList.add('bottom-sheet--active');
      
      // Setup touch gestures for dismissal
      const handle = sheet.querySelector('.bottom-sheet__handle');
      if (handle) {
        handle.addEventListener('touchstart', this.handleTouchStart.bind(this));
        handle.addEventListener('touchmove', this.handleTouchMove.bind(this));
        handle.addEventListener('touchend', this.handleTouchEnd.bind(this));
      }
      
      // Close on backdrop click
      if (backdrop) {
        backdrop.addEventListener('click', () => this.close(sheetId));
      }
      
      // Close on Escape
      document.addEventListener('keydown', this.handleEscape);
    },
    
    close(sheetId) {
      const sheet = document.getElementById(sheetId);
      const backdrop = document.getElementById(`${sheetId}-backdrop`) || 
                       document.querySelector('.bottom-sheet-backdrop');
      
      if (!sheet) return;
      
      sheet.classList.remove('bottom-sheet--active');
      sheet.style.transform = '';
      if (backdrop) backdrop.classList.remove('bottom-sheet-backdrop--active');
      
      document.body.style.overflow = '';
      document.removeEventListener('keydown', this.handleEscape);
      
      this.activeSheet = null;
    },
    
    handleTouchStart(e) {
      this.isDragging = true;
      this.startY = e.touches[0].clientY;
    },
    
    handleTouchMove(e) {
      if (!this.isDragging || !this.activeSheet) return;
      
      this.currentY = e.touches[0].clientY;
      const diff = this.currentY - this.startY;
      
      if (diff > 0) {
        this.activeSheet.style.transform = `translateY(${diff}px)`;
        this.activeSheet.style.transition = 'none';
      }
    },
    
    handleTouchEnd() {
      if (!this.isDragging || !this.activeSheet) return;
      
      const diff = this.currentY - this.startY;
      this.activeSheet.style.transition = '';
      
      if (diff > 100) {
        this.close(this.activeSheet.id);
      } else {
        this.activeSheet.style.transform = '';
      }
      
      this.isDragging = false;
    },
    
    handleEscape(e) {
      if (e.key === 'Escape' && BottomSheet.activeSheet) {
        BottomSheet.close(BottomSheet.activeSheet.id);
      }
    }
  };

  // ==========================================================================
  // TOGGLE COMPONENT
  // Enhanced toggle with ripple effect
  // ==========================================================================

  const Toggle = {
    init() {
      document.querySelectorAll('.toggle').forEach(toggle => {
        const input = toggle.querySelector('.toggle__input');
        if (!input) return;
        
        // Add haptic feedback on iOS
        input.addEventListener('change', () => {
          if ('vibrate' in navigator) {
            navigator.vibrate(10);
          }
        });
      });
    }
  };

  // ==========================================================================
  // FORM VALIDATION
  // Real-time validation with accessible error messages
  // ==========================================================================

  const FormValidation = {
    init() {
      document.querySelectorAll('form[data-validate]').forEach(form => {
        form.addEventListener('submit', this.handleSubmit.bind(this));
        
        form.querySelectorAll('.form-input').forEach(input => {
          input.addEventListener('blur', () => this.validateField(input));
          input.addEventListener('input', () => {
            if (input.classList.contains('form-input--error')) {
              this.validateField(input);
            }
          });
        });
      });
    },
    
    handleSubmit(e) {
      const form = e.target;
      const inputs = form.querySelectorAll('.form-input[required]');
      let isValid = true;
      
      inputs.forEach(input => {
        if (!this.validateField(input)) {
          isValid = false;
        }
      });
      
      if (!isValid) {
        e.preventDefault();
        const firstError = form.querySelector('.form-input--error');
        if (firstError) firstError.focus();
      }
    },
    
    validateField(input) {
      const value = input.value.trim();
      const errorEl = input.parentElement.querySelector('.form-error');
      let isValid = true;
      let message = '';
      
      // Required validation
      if (input.hasAttribute('required') && !value) {
        isValid = false;
        message = 'This field is required';
      }
      
      // Email validation
      if (input.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
          isValid = false;
          message = 'Please enter a valid email address';
        }
      }
      
      // Update UI
      if (isValid) {
        input.classList.remove('form-input--error');
        if (errorEl) errorEl.textContent = '';
        input.removeAttribute('aria-invalid');
      } else {
        input.classList.add('form-input--error');
        if (errorEl) errorEl.textContent = message;
        input.setAttribute('aria-invalid', 'true');
      }
      
      return isValid;
    }
  };

  // ==========================================================================
  // PULL TO REFRESH (Disabled for native feel)
  // ==========================================================================

  const PullToRefresh = {
    init() {
      // Prevent default pull-to-refresh on iOS within the app
      document.body.style.overscrollBehaviorY = 'contain';
    }
  };

  // ==========================================================================
  // HAPTIC FEEDBACK
  // iOS-style haptic feedback for interactions
  // ==========================================================================

  const Haptics = {
    light() {
      if ('vibrate' in navigator) {
        navigator.vibrate(10);
      }
    },
    
    medium() {
      if ('vibrate' in navigator) {
        navigator.vibrate(20);
      }
    },
    
    heavy() {
      if ('vibrate' in navigator) {
        navigator.vibrate([30, 10, 30]);
      }
    }
  };

  // ==========================================================================
  // SWIPE ACTIONS
  // Swipe-to-reveal actions on list items
  // ==========================================================================

  const SwipeActions = {
    init() {
      document.querySelectorAll('[data-swipeable]').forEach(item => {
        let startX = 0;
        let currentX = 0;
        let isDragging = false;
        
        item.addEventListener('touchstart', (e) => {
          startX = e.touches[0].clientX;
          isDragging = true;
          item.style.transition = 'none';
        });
        
        item.addEventListener('touchmove', (e) => {
          if (!isDragging) return;
          currentX = e.touches[0].clientX;
          const diff = currentX - startX;
          
          // Only allow left swipe
          if (diff < 0 && diff > -100) {
            item.style.transform = `translateX(${diff}px)`;
          }
        });
        
        item.addEventListener('touchend', () => {
          isDragging = false;
          item.style.transition = '';
          
          const diff = currentX - startX;
          if (diff < -60) {
            item.style.transform = 'translateX(-80px)';
            item.classList.add('swipe-open');
          } else {
            item.style.transform = '';
            item.classList.remove('swipe-open');
          }
        });
      });
    }
  };

  // ==========================================================================
  // INITIALIZATION
  // ==========================================================================

  function init() {
    ThemeManager.init();
    Toast.init();
    Toggle.init();
    FormValidation.init();
    PullToRefresh.init();
    SwipeActions.init();
    
    // Expose to global scope for use in templates
    window.CSU = {
      ThemeManager,
      Toast,
      Modal,
      BottomSheet,
      Haptics
    };
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
