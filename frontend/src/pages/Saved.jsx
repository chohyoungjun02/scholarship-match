import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { ddayOf, ScholarshipRow, ScholarshipSheet } from '../components/Scholarship.jsx'
import { useToast } from '../components/ui.jsx'

// 저장한 지원: 마감 빠른 순, 7일 이내는 위에서 알림
export default function Saved() {
  const [items, setItems] = useState(null)
  const [selected, setSelected] = useState(null)
  const [toast, showToast] = useToast()

  useEffect(() => {
    api('/saved').then((d) => setItems(d.items)).catch((e) => showToast(e.message))
  }, [showToast])

  const onSavedChange = (item, saved) => {
    setItems(saved ? items : items.filter((i) => i.id !== item.id))
    setSelected(saved ? { ...item, saved } : null)
    showToast(saved ? '저장했어요' : '저장을 취소했어요')
  }
  const soon = (items || []).filter((i) => ddayOf(i.deadline) !== null && ddayOf(i.deadline) <= 7)

  return (
    <div className="screen">
      <h1 className="headline" style={{ marginBottom: 8 }}>저장한 지원</h1>
      <p className="sub" style={{ marginBottom: 20 }}>마감 7일 전부터 홈 화면에서 알려드려요</p>
      {soon.length > 0 && (
        <div className="alert-list"><b>⏰ {soon.length}개가 7일 안에 마감돼요</b></div>
      )}
      <div className="list">
        {!items && [1, 2, 3].map((i) => <div key={i} className="skeleton" />)}
        {items?.length === 0 && (
          <div className="empty"><span className="emoji">☆</span>아직 저장한 지원이 없어요.<br />공고를 열고 '저장하고 마감 알림 받기'를 눌러 보세요.</div>
        )}
        {items?.map((item) => <ScholarshipRow key={item.id} item={item} onClick={setSelected} />)}
      </div>
      <ScholarshipSheet item={selected} onClose={() => setSelected(null)} onSavedChange={onSavedChange} />
      {toast}
    </div>
  )
}
