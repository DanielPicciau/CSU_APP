/**
 * CSU Tracker - Offline Storage System
 * =====================================
 * Provides offline-first data storage using IndexedDB.
 * Allows the app to work completely without internet.
 * 
 * Features:
 * - Store daily entries locally
 * - Queue form submissions for sync when online
 * - Cache user data for instant display
 * - Background sync when connection restored
 */

(function () {
  'use strict';

  const DB_NAME = 'csu-tracker';
  const DB_VERSION = 1;

  const OfflineStorage = {
    db: null,
    isOnline: navigator.onLine,
    syncQueue: [],
    isResetting: false,

    /**
     * Initialize the offline storage system
     */
    async init() {
      try {
        this.db = await this.openDatabase();
        this.setupOnlineListeners();
        this.loadSyncQueue();

        // Try to sync any pending items (fire-and-forget with error handling)
        if (this.isOnline) {
          this.syncPendingItems().catch(err =>
            console.warn('[OfflineStorage] Background sync failed:', err)
          );
        }

        console.log('[OfflineStorage] Initialized successfully');
        return true;
      } catch (error) {
        console.error('[OfflineStorage] Failed to initialize:', error);
        return false;
      }
    },

    /**
     * Open IndexedDB database
     */
    openDatabase() {
      return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
          const db = event.target.result;

          // Store for daily entries
          if (!db.objectStoreNames.contains('entries')) {
            const entriesStore = db.createObjectStore('entries', { keyPath: 'date' });
            entriesStore.createIndex('synced', 'synced', { unique: false });
            entriesStore.createIndex('updatedAt', 'updatedAt', { unique: false });
          }

          // Store for pending form submissions (sync queue)
          if (!db.objectStoreNames.contains('syncQueue')) {
            const syncStore = db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
            syncStore.createIndex('createdAt', 'createdAt', { unique: false });
            syncStore.createIndex('endpoint', 'endpoint', { unique: false });
          }

          // Store for cached user data
          if (!db.objectStoreNames.contains('userData')) {
            db.createObjectStore('userData', { keyPath: 'key' });
          }

          // Store for cached pages
          if (!db.objectStoreNames.contains('pageCache')) {
            const pageStore = db.createObjectStore('pageCache', { keyPath: 'url' });
            pageStore.createIndex('cachedAt', 'cachedAt', { unique: false });
          }
        };
      });
    },

    /**
     * Setup online/offline event listeners
     */
    setupOnlineListeners() {
      window.addEventListener('online', () => {
        this.isOnline = true;
        console.log('[OfflineStorage] Back online - syncing...');
        this.showOnlineStatus(true);
        this.syncPendingItems().catch(err =>
          console.warn('[OfflineStorage] Sync after reconnect failed:', err)
        );
      });

      window.addEventListener('offline', () => {
        this.isOnline = false;
        console.log('[OfflineStorage] Gone offline');
        this.showOnlineStatus(false);
      });
    },

    /**
     * Reset IndexedDB when it becomes corrupted or schema mismatched.
     */
    async resetDatabase(reason) {
      if (this.isResetting) return;
      this.isResetting = true;
      console.warn('[OfflineStorage] Resetting database:', reason);

      try {
        if (this.db) {
          try { this.db.close(); } catch (e) { }
        }
        await new Promise((resolve, reject) => {
          const request = indexedDB.deleteDatabase(DB_NAME);
          request.onsuccess = () => resolve();
          request.onerror = () => reject(request.error);
          request.onblocked = () => resolve();
        });
        this.db = await this.openDatabase();
        this.syncQueue = [];
      } catch (error) {
        console.error('[OfflineStorage] Database reset failed:', error);
      } finally {
        this.isResetting = false;
      }
    },

    /**
     * Show online/offline status indicator
     */
    showOnlineStatus(online) {
      let indicator = document.getElementById('offline-indicator');

      if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'offline-indicator';
        indicator.style.cssText = `
          position: fixed;
          bottom: calc(env(safe-area-inset-bottom, 0px) + 70px);
          left: 50%;
          transform: translateX(-50%);
          padding: 8px 16px;
          border-radius: 20px;
          font-size: 14px;
          font-weight: 500;
          z-index: 9998;
          transition: opacity 0.3s, transform 0.3s;
          box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        `;
        document.body.appendChild(indicator);
      }

      if (online) {
        indicator.textContent = '✓ Back online';
        indicator.style.background = '#22c55e';
        indicator.style.color = 'white';
        indicator.style.opacity = '1';
        indicator.style.transform = 'translateX(-50%) translateY(0)';

        // Hide after 3 seconds
        setTimeout(() => {
          indicator.style.opacity = '0';
          indicator.style.transform = 'translateX(-50%) translateY(10px)';
        }, 3000);
      } else {
        indicator.textContent = '📴 Offline - data will sync when online';
        indicator.style.background = '#f59e0b';
        indicator.style.color = 'white';
        indicator.style.opacity = '1';
        indicator.style.transform = 'translateX(-50%) translateY(0)';
      }
    },

    // =========================================================================
    // ENTRIES STORAGE
    // =========================================================================

    /**
     * Save a daily entry locally
     */
    async saveEntry(entry) {
      const tx = this.db.transaction('entries', 'readwrite');
      const store = tx.objectStore('entries');

      const record = {
        date: entry.date,
        score: entry.score,
        itchScore: entry.itchScore,
        hiveScore: entry.hiveScore,
        notes: entry.notes || '',
        photoUrl: entry.photoUrl || null,
        triggers: entry.triggers || [],
        qolData: entry.qolData || {},
        synced: false,
        updatedAt: new Date().toISOString()
      };

      return new Promise((resolve, reject) => {
        const request = store.put(record);
        request.onsuccess = () => resolve(record);
        request.onerror = () => reject(request.error);
      });
    },

    /**
     * Get a daily entry by date
     */
    async getEntry(date) {
      const tx = this.db.transaction('entries', 'readonly');
      const store = tx.objectStore('entries');

      return new Promise((resolve, reject) => {
        const request = store.get(date);
        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => reject(request.error);
      });
    },

    /**
     * Get all entries in a date range
     */
    async getEntries(startDate, endDate) {
      const tx = this.db.transaction('entries', 'readonly');
      const store = tx.objectStore('entries');

      return new Promise((resolve, reject) => {
        const entries = [];
        const range = IDBKeyRange.bound(startDate, endDate);
        const request = store.openCursor(range);

        request.onsuccess = (event) => {
          const cursor = event.target.result;
          if (cursor) {
            entries.push(cursor.value);
            cursor.continue();
          } else {
            resolve(entries);
          }
        };
        request.onerror = () => reject(request.error);
      });
    },

    /**
     * Get unsynced entries
     * Note: We use getAll + filter instead of IDBKeyRange.only(false)
     * because IndexedDB boolean index queries are unreliable across
     * browsers and can throw DataError when stored values have
     * mismatched types (e.g. after schema changes or partial writes).
     */
    async getUnsyncedEntries() {
      const tx = this.db.transaction('entries', 'readonly');
      const store = tx.objectStore('entries');

      return new Promise((resolve, reject) => {
        const request = store.getAll();

        request.onsuccess = () => {
          const all = request.result || [];
          resolve(all.filter(entry => !entry.synced));
        };
        request.onerror = () => reject(request.error);
      });
    },

    /**
     * Mark entry as synced
     */
    async markEntrySynced(date) {
      const entry = await this.getEntry(date);
      if (entry) {
        entry.synced = true;
        const tx = this.db.transaction('entries', 'readwrite');
        const store = tx.objectStore('entries');
        store.put(entry);
      }
    },

    // =========================================================================
    // SYNC QUEUE
    // =========================================================================

    /**
     * Add an item to the sync queue
     */
    async queueForSync(endpoint, method, data) {
      const tx = this.db.transaction('syncQueue', 'readwrite');
      const store = tx.objectStore('syncQueue');

      const item = {
        endpoint,
        method,
        data,
        createdAt: new Date().toISOString(),
        retries: 0
      };

      return new Promise((resolve, reject) => {
        const request = store.add(item);
        request.onsuccess = () => {
          console.log('[OfflineStorage] Queued for sync:', endpoint);
          resolve(request.result);
        };
        request.onerror = () => reject(request.error);
      });
    },

    /**
     * Load sync queue from IndexedDB
     */
    async loadSyncQueue() {
      const tx = this.db.transaction('syncQueue', 'readonly');
      const store = tx.objectStore('syncQueue');

      return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => {
          this.syncQueue = request.result || [];
          resolve(this.syncQueue);
        };
        request.onerror = () => reject(request.error);
      });
    },

    /**
     * Sync all pending items
     */
    async syncPendingItems() {
      if (!this.isOnline) return;

      // Sync entries
      let unsyncedEntries = [];
      try {
        unsyncedEntries = await this.getUnsyncedEntries();
      } catch (error) {
        if (error && (error.name === 'DataError' || error.name === 'InvalidStateError')) {
          await this.resetDatabase(error.name);
          return;
        }
        throw error;
      }
      for (const entry of unsyncedEntries) {
        try {
          await this.syncEntry(entry);
          await this.markEntrySynced(entry.date);
        } catch (error) {
          console.error('[OfflineStorage] Failed to sync entry:', entry.date, error);
        }
      }

      // Sync queue items
      await this.loadSyncQueue();
      for (const item of this.syncQueue) {
        try {
          await this.processSyncItem(item);
          await this.removeSyncItem(item.id);
        } catch (error) {
          console.error('[OfflineStorage] Failed to sync item:', item.id, error);
          await this.incrementRetryCount(item.id);
        }
      }
    },

    /**
     * Sync a single entry to the server
     */
    async syncEntry(entry) {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        document.cookie.match(/csrftoken=([^;]+)/)?.[1];

      const response = await fetch(`/api/tracking/entries/${entry.date}/`, {
        method: 'PUT',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken || ''
        },
        body: JSON.stringify({
          score: entry.score,
          itch_score: entry.itchScore,
          hive_score: entry.hiveScore,
          notes: entry.notes,
          triggers: entry.triggers
        })
      });

      if (!response.ok) {
        throw new Error(`Sync failed: ${response.status}`);
      }

      return response.json();
    },

    /**
     * Process a sync queue item
     */
    async processSyncItem(item) {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        document.cookie.match(/csrftoken=([^;]+)/)?.[1];

      const response = await fetch(item.endpoint, {
        method: item.method,
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken || ''
        },
        body: JSON.stringify(item.data)
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      return response.json();
    },

    /**
     * Remove item from sync queue
     */
    async removeSyncItem(id) {
      const tx = this.db.transaction('syncQueue', 'readwrite');
      const store = tx.objectStore('syncQueue');
      store.delete(id);
    },

    /**
     * Increment retry count for failed sync
     */
    async incrementRetryCount(id) {
      const tx = this.db.transaction('syncQueue', 'readwrite');
      const store = tx.objectStore('syncQueue');

      return new Promise((resolve, reject) => {
        const request = store.get(id);
        request.onsuccess = () => {
          const item = request.result;
          if (item) {
            item.retries = (item.retries || 0) + 1;
            // Remove if too many retries
            if (item.retries > 5) {
              store.delete(id);
            } else {
              store.put(item);
            }
          }
          resolve();
        };
        request.onerror = () => reject(request.error);
      });
    },

    // =========================================================================
    // USER DATA CACHE
    // =========================================================================

    /**
     * Cache user data
     */
    async cacheUserData(key, data) {
      const tx = this.db.transaction('userData', 'readwrite');
      const store = tx.objectStore('userData');

      return new Promise((resolve, reject) => {
        const request = store.put({
          key,
          data,
          cachedAt: new Date().toISOString()
        });
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    },

    /**
     * Get cached user data
     */
    async getCachedUserData(key) {
      const tx = this.db.transaction('userData', 'readonly');
      const store = tx.objectStore('userData');

      return new Promise((resolve, reject) => {
        const request = store.get(key);
        request.onsuccess = () => resolve(request.result?.data || null);
        request.onerror = () => reject(request.error);
      });
    },

    // =========================================================================
    // PAGE CACHE
    // =========================================================================

    /**
     * Cache a page's HTML
     */
    async cachePage(url, html) {
      const tx = this.db.transaction('pageCache', 'readwrite');
      const store = tx.objectStore('pageCache');

      return new Promise((resolve, reject) => {
        const request = store.put({
          url,
          html,
          cachedAt: new Date().toISOString()
        });
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    },

    /**
     * Get cached page
     */
    async getCachedPage(url) {
      const tx = this.db.transaction('pageCache', 'readonly');
      const store = tx.objectStore('pageCache');

      return new Promise((resolve, reject) => {
        const request = store.get(url);
        request.onsuccess = () => resolve(request.result?.html || null);
        request.onerror = () => reject(request.error);
      });
    },

    // =========================================================================
    // FORM INTERCEPTION
    // =========================================================================

    /**
     * Intercept form submissions for offline support
     */
    setupFormInterception() {
      document.addEventListener('submit', async (e) => {
        const form = e.target;

        // Only intercept specific forms
        if (!form.hasAttribute('data-offline-enabled')) return;

        // If online, let form submit normally
        if (this.isOnline) return;

        e.preventDefault();

        // Collect form data
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Queue for sync
        await this.queueForSync(
          form.action,
          form.method.toUpperCase() || 'POST',
          data
        );

        // Show success message
        this.showOfflineSaveMessage();

        // If it's an entry form, save locally too
        if (form.action.includes('/tracking/') || form.action.includes('/log')) {
          const today = new Date().toISOString().split('T')[0];
          await this.saveEntry({
            date: data.date || today,
            score: parseInt(data.score || 0),
            itchScore: parseInt(data.itch_score || 0),
            hiveScore: parseInt(data.hive_score || 0),
            notes: data.notes || ''
          });
        }
      });
    },

    /**
     * Show offline save confirmation
     */
    showOfflineSaveMessage() {
      const message = document.createElement('div');
      message.className = 'offline-save-message';
      message.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <span>Saved offline - will sync when online</span>
      `;
      message.style.cssText = `
        position: fixed;
        bottom: calc(env(safe-area-inset-bottom, 0px) + 120px);
        left: 50%;
        transform: translateX(-50%);
        background: #3b82f6;
        color: white;
        padding: 12px 20px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        z-index: 9999;
        animation: slideUp 0.3s ease;
      `;

      document.body.appendChild(message);

      setTimeout(() => {
        message.style.animation = 'slideDown 0.3s ease';
        setTimeout(() => message.remove(), 300);
      }, 3000);
    }
  };

  // Add animations
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideUp {
      from { transform: translateX(-50%) translateY(20px); opacity: 0; }
      to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
    @keyframes slideDown {
      from { transform: translateX(-50%) translateY(0); opacity: 1; }
      to { transform: translateX(-50%) translateY(20px); opacity: 0; }
    }
  `;
  document.head.appendChild(style);

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => OfflineStorage.init());
  } else {
    OfflineStorage.init();
  }

  // Expose globally
  window.OfflineStorage = OfflineStorage;

})();
