// CSU Tracker Service Worker
const CACHE_NAME = 'csu-tracker-v3';
const OFFLINE_URL = '/offline/';

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/offline/',
    '/static/icons/icon-192x192.png',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - stale-while-revalidate for navigation, network-first for others
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // Skip API requests (don't cache)
    if (event.request.url.includes('/api/')) return;
    
    // Use stale-while-revalidate for navigation requests (instant page loads)
    if (event.request.mode === 'navigate') {
        event.respondWith(
            caches.match(event.request).then((cachedResponse) => {
                // Start network fetch in background
                const networkFetch = fetch(event.request).then((networkResponse) => {
                    // Only cache successful, non-redirect responses (Safari compatibility)
                    if (networkResponse.status === 200 && !networkResponse.redirected && networkResponse.type !== 'opaqueredirect') {
                        const responseClone = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, responseClone);
                        });
                    }
                    return networkResponse;
                });
                
                // Return cached response immediately, or wait for network
                return cachedResponse || networkFetch.catch(() => caches.match(OFFLINE_URL));
            })
        );
        return;
    }
    
    // Network-first for other resources (CSS, JS, images)
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Only cache successful, non-redirect responses (Safari compatibility)
                if (response.status === 200 && !response.redirected && response.type !== 'opaqueredirect') {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            })
            .catch(() => {
                // Return cached response or offline page
                return caches.match(event.request)
                    .then((response) => {
                        if (response) {
                            return response;
                        }
                        return new Response('Offline', { status: 503 });
                    });
            })
    );
});

// Push event - handle incoming push notifications
self.addEventListener('push', (event) => {
    console.log('Push received:', event);
    
    let data = {
        title: 'CSU Tracker',
        body: 'Time to log your daily score!',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        tag: 'csu-reminder',
        data: { url: '/' }
    };
    
    if (event.data) {
        try {
            const payload = event.data.json();
            data = { ...data, ...payload };
        } catch (e) {
            console.error('Failed to parse push data:', e);
        }
    }
    
    const options = {
        body: data.body,
        icon: data.icon,
        badge: data.badge,
        tag: data.tag,
        data: data.data,
        vibrate: [100, 50, 100],
        requireInteraction: true,
        actions: [
            { action: 'log', title: 'Log Now' },
            { action: 'dismiss', title: 'Later' }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event);
    
    event.notification.close();
    
    const action = event.action;
    let url = '/';
    
    if (action === 'log' || !action) {
        url = event.notification.data?.url || '/tracking/log/';
    }
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Focus existing window if available
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        client.navigate(url);
                        return client.focus();
                    }
                }
                // Open new window
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});

// Handle notification close
self.addEventListener('notificationclose', (event) => {
    console.log('Notification closed:', event);
});
