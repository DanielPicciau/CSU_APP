/**
 * CSU Tracker - Performance Optimizations & Smooth Interactions
 * ==============================================================
 * Handles lazy loading, smooth scrolling, animations, and optimized DOM updates
 */

(function () {
  'use strict';

  // ==========================================================================
  // PERFORMANCE UTILITIES
  // ==========================================================================

  const Performance = {
    /**
     * Debounce function execution
     */
    debounce(func, wait = 100) {
      let timeout;
      return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
      };
    },

    /**
     * Throttle function execution
     */
    throttle(func, limit = 16) {
      let inThrottle;
      return function (...args) {
        if (!inThrottle) {
          func.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    },

    /**
     * Request idle callback polyfill
     */
    requestIdleCallback(callback) {
      if ('requestIdleCallback' in window) {
        return window.requestIdleCallback(callback);
      }
      return setTimeout(() => callback({ didTimeout: false, timeRemaining: () => 50 }), 1);
    },

    /**
     * Batch DOM updates using requestAnimationFrame
     */
    batchDOMUpdates(updates) {
      requestAnimationFrame(() => {
        updates.forEach(update => update());
      });
    }
  };

  // ==========================================================================
  // INTERSECTION OBSERVER FOR SCROLL ANIMATIONS — REMOVED
  // (All scroll-animate / fade-in / stagger animations stripped for perf)
  // ==========================================================================

  const ScrollAnimations = { init() { }, observe() { } };

  // ==========================================================================
  // SMOOTH PAGE TRANSITIONS — REMOVED
  // ==========================================================================

  const PageTransitions = { init() { } };

  // ==========================================================================
  // OPTIMIZED TOUCH INTERACTIONS
  // ==========================================================================

  const TouchOptimizations = {
    init() {
      // Passive event listeners for scroll performance
      this.setupPassiveScrolling();

      // Optimized touch feedback
      this.setupTouchFeedback();

      // Prevent 300ms tap delay
      this.setupFastClick();
    },

    setupPassiveScrolling() {
      // Add passive flag to scroll/touch events for better performance
      const passiveSupported = this.checkPassiveSupport();
      const options = passiveSupported ? { passive: true } : false;

      document.addEventListener('touchstart', () => { }, options);
      document.addEventListener('touchmove', () => { }, options);
      document.addEventListener('wheel', () => { }, options);
    },

    checkPassiveSupport() {
      let passiveSupported = false;
      try {
        const options = {
          get passive() {
            passiveSupported = true;
            return false;
          }
        };
        window.addEventListener('test', null, options);
        window.removeEventListener('test', null, options);
      } catch (err) {
        passiveSupported = false;
      }
      return passiveSupported;
    },

    setupTouchFeedback() {
      // Add touch feedback to interactive elements (CSS touch-action only, no animation classes)
      const interactiveElements = document.querySelectorAll(
        'button, a, .radio-card, .btn, [role="button"]'
      );

      interactiveElements.forEach(el => {
        el.classList.add('touch-action-manipulation');
      });
    },

    setupFastClick() {
      // CSS touch-action: manipulation handles this in modern browsers
      document.documentElement.style.touchAction = 'manipulation';
    }
  };

  // ==========================================================================
  // LAZY LOADING IMAGES
  // ==========================================================================

  const LazyLoading = {
    observer: null,

    init() {
      if (!('IntersectionObserver' in window)) {
        // Fallback: load all images immediately
        this.loadAllImages();
        return;
      }

      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              this.loadImage(entry.target);
              this.observer.unobserve(entry.target);
            }
          });
        },
        {
          rootMargin: '100px 0px'
        }
      );

      document.querySelectorAll('img[data-src], [data-bg]').forEach(el => {
        this.observer.observe(el);
      });
    },

    loadImage(el) {
      if (el.dataset.src) {
        el.src = el.dataset.src;
        el.removeAttribute('data-src');
      }
      if (el.dataset.bg) {
        el.style.backgroundImage = `url(${el.dataset.bg})`;
        el.removeAttribute('data-bg');
      }
      el.classList.add('loaded');
    },

    loadAllImages() {
      document.querySelectorAll('img[data-src]').forEach(img => {
        img.src = img.dataset.src;
      });
    }
  };

  // ==========================================================================
  // ANIMATED COUNTERS — REMOVED
  // ==========================================================================

  const AnimatedCounters = { init() { } };

  // ==========================================================================
  // CHART BAR ANIMATIONS — REMOVED
  // ==========================================================================

  const ChartAnimations = { init() { } };

  // ==========================================================================
  // STAGGERED LIST ANIMATIONS — REMOVED
  // ==========================================================================

  const StaggeredLists = { init() { } };

  // ==========================================================================
  // FORM ENHANCEMENTS
  // ==========================================================================

  const FormEnhancements = {
    init() {
      // Radio card animations
      this.setupRadioCards();

      // Input focus animations
      this.setupInputAnimations();

      // Form submission feedback
      this.setupFormSubmission();
    },

    setupRadioCards() {
      document.querySelectorAll('.radio-card').forEach(card => {
        const input = card.querySelector('input[type="radio"]');
        if (input) {
          input.addEventListener('change', () => {
            // Remove active class from siblings
            const parent = card.parentElement;
            parent.querySelectorAll('.radio-card').forEach(c => {
              c.classList.remove('selected');
            });

            // Add to selected
            card.classList.add('selected');
          });
        }
      });
    },

    setupInputAnimations() {
      // No-op: animation classes removed
    },

    setupFormSubmission() {
      document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
          const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
          if (submitBtn && !submitBtn.disabled) {
            // Add loading state
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner spinner-sm"></span> Saving...';
            submitBtn.disabled = true;
            submitBtn.classList.add('opacity-75');

            // Re-enable after a timeout (in case of error)
            setTimeout(() => {
              if (submitBtn.disabled) {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                submitBtn.classList.remove('opacity-75');
              }
            }, 10000);
          }
        });
      });
    }
  };

  // ==========================================================================
  // SCORE DISPLAY ANIMATIONS — REMOVED
  // ==========================================================================

  const ScoreAnimations = { init() { } };

  // ==========================================================================
  // PREFETCHING FOR FASTER NAVIGATION
  // ==========================================================================

  const Prefetching = {
    prefetchedUrls: new Set(),

    init() {
      // Prefetch links on hover for faster navigation
      document.addEventListener('mouseover', Performance.debounce((e) => {
        const link = e.target.closest('a[href^="/"]');
        if (link) {
          this.prefetchUrl(link.href);
        }
      }, 100));

      // Also prefetch on touchstart for mobile
      document.addEventListener('touchstart', (e) => {
        const link = e.target.closest('a[href^="/"]');
        if (link) {
          this.prefetchUrl(link.href);
        }
      }, { passive: true });
    },

    prefetchUrl(url) {
      if (this.prefetchedUrls.has(url)) return;
      if (url.includes('/api/') || url.includes('/logout')) return;

      this.prefetchedUrls.add(url);

      // Use link prefetch for supported browsers
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = url;
      link.as = 'document';
      document.head.appendChild(link);
    }
  };

  // ==========================================================================
  // SMOOTH SCROLL
  // ==========================================================================

  const SmoothScroll = {
    init() {
      // Enable smooth scrolling for anchor links
      document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
          const targetId = anchor.getAttribute('href');
          if (targetId === '#') return;

          const target = document.querySelector(targetId);
          if (target) {
            e.preventDefault();
            target.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            });
          }
        });
      });
    }
  };

  // ==========================================================================
  // MEMORY OPTIMIZATION — REMOVED (no animations to clean up)
  // ==========================================================================

  const MemoryOptimization = { init() { } };

  // ==========================================================================
  // BOTTOM NAV ANIMATIONS — REMOVED
  // ==========================================================================

  const BottomNavAnimations = { init() { } };

  // ==========================================================================
  // INITIALIZE ALL MODULES
  // ==========================================================================

  function init() {
    // Initialize immediately
    TouchOptimizations.init();
    PageTransitions.init();
    BottomNavAnimations.init();

    // Initialize after DOM is interactive
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initDOMDependentModules);
    } else {
      initDOMDependentModules();
    }
  }

  function initDOMDependentModules() {
    ScrollAnimations.init();
    FormEnhancements.init();
    ScoreAnimations.init();
    ChartAnimations.init();
    StaggeredLists.init();
    SmoothScroll.init();
    MemoryOptimization.init();

    // Initialize less critical features during idle time
    Performance.requestIdleCallback(() => {
      LazyLoading.init();
      Prefetching.init();
      AnimatedCounters.init();
    });
  }

  // Expose utilities globally for external use
  window.CSUPerformance = {
    Performance,
    ScrollAnimations,
    AnimatedCounters,
    StaggeredLists
  };

  // Initialize
  init();

})();
