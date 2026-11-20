import { useState } from 'react'
import { api } from '../api.js'
import { BottomSheet, Icon, shortDate } from './ui.jsx'

export const STATUS = {
  eligible: '지원 가능',
  check: '확인 필요',
  ineligible: '해당 없음',
}

export const KINDS = ['장학금', '생활지원', '국비교육', '지역사업']

// 학교 공지 🎓 / 한국장학재단 🏛️ / 생활지원 🏠 / 국비교육 📚 / 지역사업 💼
const iconOf = (item) => {
  if (item.kind === '생활지원') return ['life', '🏠']
  if (item.kind === '국비교육') return ['edu', '📚']
  if (item.kind === '지역사업') return ['kosaf', '💼']
  return item.university_id ? ['school', '🎓'] : ['kosaf', '🏛️']
}

// 오늘(한국 시간) 기준 마감까지 남은 날짜, 마감일 모르면 null
export function ddayOf(deadline) {
  if (!deadline) return null
  const today = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }))
  today.setHours(0, 0, 0, 0)
  return Math.round((new Date(`${deadline}T00:00:00`) - today) / 86400000)
}

export function DdayBadge({ deadline }) {
  const d = ddayOf(deadline)
  if (d === null) return null
  return <span className={`badge dday ${d <= 7 ? 'soon' : ''}`}>{d === 0 ? '오늘 마감' : `D-${d}`}</span>
}

// 분류 탭 + 정렬 (최신순 / 마감순)
export function useCardFilter(items) {
  const [kind, setKind] = useState('')
  const [sort, setSort] = useState('recent')
  let shown = (items || []).filter((i) => !kind || i.kind === kind)
  if (sort === 'deadline') shown = [...shown].sort((a, b) => (a.deadline || '9999').localeCompare(b.deadline || '9999'))
  const controls = (
    <div className="filter-bar">
      <div className="chips scroll">
        {['', ...KINDS].map((k) => (
          <button key={k} type="button" className={`chip ${kind === k ? 'on' : ''}`} onClick={() => setKind(k)}>
            {k || '전체'}
          </button>
        ))}
      </div>
      <select className="select small" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="정렬">
        <option value="recent">최신순</option>
        <option value="deadline">마감순</option>
      </select>
    </div>
  )
  return [controls, shown]
}

export function ScholarshipRow({ item, onClick }) {
  const amount = item.match?.amount || item.amount_text
  return (
    <button className="list-row" onClick={() => onClick(item)}>
      <div className={`icon ${iconOf(item)[0]}`}>{iconOf(item)[1]}</div>
      <div className="body">
        <div className="title">{item.saved && <span className="star" aria-label="저장함">★ </span>}{item.title}</div>
        <div className="meta">
          {item.kind} · {item.agency || item.source}
          {item.posted_at && ` · ${shortDate(item.posted_at)}`}
          {amount && <> · <span className="amount">{amount}</span></>}
        </div>
      </div>
      <DdayBadge deadline={item.deadline} />
      <span className="chev">{Icon.chevronRight}</span>
    </button>
  )
}

const ageText = (item) =>
  item.min_age && item.max_age ? (item.min_age === item.max_age ? `만 ${item.min_age}세` : `만 ${item.min_age}~${item.max_age}세`)
    : item.min_age ? `만 ${item.min_age}세 이상` : item.max_age ? `만 ${item.max_age}세 이하` : null

// onSavedChange 가 있을 때만 저장 버튼을 보여 준다
export function ScholarshipSheet({ item, onClose, onSavedChange }) {
  const m = item?.match
  const [busy, setBusy] = useState(false)

  const toggleSave = async () => {
    setBusy(true)
    try {
      await api(`/saved/${item.id}`, { method: item.saved ? 'DELETE' : 'PUT' })
      onSavedChange(item, !item.saved)
    } finally {
      setBusy(false)
    }
  }

  // 공통 카드 필드: 얼마 / 누가 / 언제까지 / 어디서 — 값이 있는 것만
  const fields = item && [
    ['지원 내용', m?.amount || item.amount_text],
    // 원문에 나이가 이미 있으면 정리한 나이를 덧붙이지 않음
    ['대상', [item.target_text, !/만\s*\d/.test(item.target_text || '') && ageText(item)].filter(Boolean).join(' · ')],
    ['신청 기간', item.deadline && `${item.apply_start || ''} ~ ${item.deadline}`],
    ['운영 기관', item.agency || item.source],
    ['지역', item.region],
    ['최종 확인일', item.verified_at],
  ].filter(([, v]) => v)

  return (
    <BottomSheet open={!!item} onClose={onClose}>
      {item && (
        <>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <span className="badge src">{item.kind}</span>
            {m && <span className={`badge ${m.status}`}>{STATUS[m.status]}</span>}
            <DdayBadge deadline={item.deadline} />
          </div>
          <h2>{item.title}</h2>

          <dl className="card-fields">
            {fields.map(([k, v]) => (<div key={k}><dt>{k}</dt><dd>{v}</dd></div>))}
          </dl>

          {m && (m.passed.length + m.failed.length + m.unknown.length > 0 || !item.is_structured) && (
            <>
              <div className="section-title" style={{ fontSize: 17, marginTop: 8 }}>자격 조건</div>
              <ul className="cond">
                {m.passed.map((r) => <li key={r} className="ok"><span className="mark">✓</span>{r}</li>)}
                {m.failed.map((r) => <li key={r} className="no"><span className="mark">✕</span>{r}</li>)}
                {m.unknown.map((r) => <li key={r} className="unk"><span className="mark">?</span>{r}</li>)}
                {!item.is_structured && (
                  <li className="unk"><span className="mark">?</span>
                    {m.status === 'eligible' ? '공지 본문에서 읽은 조건 기준이에요. 신청 전 원문을 꼭 확인하세요.' : '자동으로 수집한 공고예요. 원문에서 자격 요건을 꼭 확인하세요.'}
                  </li>
                )}
              </ul>
            </>
          )}

          {item.description && !item.target_text && <div className="desc-box">{item.description}</div>}

          <a href={item.url.split('#')[0]} target="_blank" rel="noreferrer">
            <button className="btn">신청하러 가기</button>
          </a>
          {onSavedChange && (
            <button className="btn secondary" style={{ marginTop: 8 }} onClick={toggleSave} disabled={busy}>
              {item.saved ? '★ 저장 취소' : '☆ 저장하고 마감 알림 받기'}
            </button>
          )}
          <div className="center-link"><button className="text-btn" onClick={onClose}>닫기</button></div>
        </>
      )}
    </BottomSheet>
  )
}
