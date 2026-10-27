import { useEffect, useState } from 'react'
import { api } from './api.js'

let cache = null

// 서비스 대상 대학 목록 (경기도) - 백엔드 crawler/universities.py 기준
export function useUniversities() {
  const [items, setItems] = useState(cache || [])
  useEffect(() => {
    if (cache) return
    api('/universities').then((d) => {
      cache = d.items
      setItems(d.items)
    })
  }, [])
  return items
}
