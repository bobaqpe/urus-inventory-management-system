const PREFIX = 'urus-api-cache:v1:';

// Short-lived, business-scoped GET cache for the current tab. Authentication
// and membership (/me) data are deliberately never cached.
const TTL = [
  [/^\/products(?:\?|\/|$)/, 8_000],
  [/^\/suppliers(?:\?|\/|$)/, 20_000],
  [/^\/categories(?:\?|\/|$)/, 60_000],
  [/^\/purchase-orders(?:\?|\/|$)/, 5_000],
  [/^\/movements(?:\?|\/|$)/, 5_000],
  [/^\/dashboard\//, 8_000],
  [/^\/reports\//, 15_000],
];

function scopePrefix(userId, businessId) {
  return `${PREFIX}${encodeURIComponent(userId)}:${encodeURIComponent(businessId)}:`;
}

function removePrefix(prefix) {
  try {
    for (let i = sessionStorage.length - 1; i >= 0; i--) {
      const key = sessionStorage.key(i);
      if (key?.startsWith(prefix)) sessionStorage.removeItem(key);
    }
  } catch { /* Cache expiry remains the fallback. */ }
}

const channel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel('urus-api-cache-v1');
channel?.addEventListener('message', event => {
  if (event.data?.type === 'invalidate-business' && event.data.userId && event.data.businessId) {
    removePrefix(scopePrefix(event.data.userId, event.data.businessId));
  } else if (event.data?.type === 'clear') {
    removePrefix(PREFIX);
  }
});

function ttlFor(path) { return TTL.find(([pattern]) => pattern.test(path))?.[1] ?? 0; }

export async function cachedGet({path, userId, businessId, fetchData}) {
  const ttl = ttlFor(path);
  const key = `${scopePrefix(userId, businessId)}${path}`;
  if (ttl) {
    try {
      const saved = JSON.parse(sessionStorage.getItem(key) || 'null');
      if (saved && saved.expiresAt > Date.now() && Object.hasOwn(saved, 'data')) return saved.data;
      if (saved) sessionStorage.removeItem(key);
    } catch { /* Ignore invalid or unavailable browser storage. */ }
  }
  const data = await fetchData();
  if (ttl) {
    try { sessionStorage.setItem(key, JSON.stringify({expiresAt: Date.now() + ttl, data})); }
    catch { /* Quota/private mode must never block the live API response. */ }
  }
  return data;
}

export function invalidateBusinessCache(userId, businessId) {
  if (!userId || !businessId) return;
  removePrefix(scopePrefix(userId, businessId));
  channel?.postMessage({type:'invalidate-business', userId:String(userId), businessId:String(businessId)});
}

export function clearApiCache() {
  removePrefix(PREFIX);
  channel?.postMessage({type:'clear'});
}
