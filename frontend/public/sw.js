// 혜택모아 서비스 워커: 앱 설치(PWA) + 오프라인에서도 화면 껍데기는 뜨도록 캐시
// - /api 요청은 항상 네트워크 (장학 정보는 최신이어야 하므로 캐시하지 않음)
// - 페이지 이동: 네트워크 우선, 실패 시 캐시된 index.html
// - 정적 파일(js/css/아이콘): 캐시 우선
const CACHE = 'scholarship-v2'
const SHELL = ['/', '/manifest.webmanifest', '/icons/icon-192.png']

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/')) return

  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone()
          if (res.ok) caches.open(CACHE).then((c) => c.put('/', copy))
          return res
        })
        .catch(() => caches.match('/')),
    )
    return
  }

  e.respondWith(
    caches.match(e.request).then((hit) =>
      hit || fetch(e.request).then((res) => {
        if (res.ok) {
          const copy = res.clone()
          caches.open(CACHE).then((c) => c.put(e.request, copy))
        }
        return res
      }),
    ),
  )
})
