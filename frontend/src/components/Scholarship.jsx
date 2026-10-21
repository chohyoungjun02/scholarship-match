import { BottomSheet, Icon, shortDate } from './ui.jsx'

export const STATUS = {
  eligible: '지원 가능',
  check: '확인 필요',
  ineligible: '해당 없음',
}

const isKosaf = (item) => !item.university_id

export function ScholarshipRow({ item, onClick }) {
  const amount = item.match?.amount || item.amount_text
  return (
    <button className="list-row" onClick={() => onClick(item)}>
      <div className={`icon ${isKosaf(item) ? 'kosaf' : 'school'}`}>{isKosaf(item) ? '🏛️' : '🎓'}</div>
      <div className="body">
        <div className="title">{item.title}</div>
        <div className="meta">
          {item.source}
          {item.posted_at && ` · ${shortDate(item.posted_at)}`}
          {amount && <> · <span className="amount">{amount}</span></>}
        </div>
      </div>
      <span className="chev">{Icon.chevronRight}</span>
    </button>
  )
}

export function ScholarshipSheet({ item, onClose }) {
  const m = item?.match
  return (
    <BottomSheet open={!!item} onClose={onClose}>
      {item && (
        <>
          <div style={{ display: 'flex', gap: 6 }}>
            <span className="badge src">{item.source}</span>
            {m && <span className={`badge ${m.status}`}>{STATUS[m.status]}</span>}
            {item.posted_at && <span className="caption" style={{ alignSelf: 'center' }}>{item.posted_at}</span>}
          </div>
          <h2>{item.title}</h2>
          {(m?.amount || item.amount_text) && <div className="amount-big">{m?.amount || item.amount_text}</div>}

          {m && (m.passed.length + m.failed.length + m.unknown.length > 0 || !item.is_structured) && (
            <>
              <div className="section-title" style={{ fontSize: 17, marginTop: 8 }}>자격 조건</div>
              <ul className="cond">
                {m.passed.map((r) => <li key={r} className="ok"><span className="mark">✓</span>{r}</li>)}
                {m.failed.map((r) => <li key={r} className="no"><span className="mark">✕</span>{r}</li>)}
                {m.unknown.map((r) => <li key={r} className="unk"><span className="mark">?</span>{r}</li>)}
                {!item.is_structured && (
                  <li className="unk"><span className="mark">?</span>자동으로 수집한 공고예요. 원문에서 자격 요건을 꼭 확인하세요.</li>
                )}
              </ul>
            </>
          )}

          {item.description && <div className="desc-box">{item.description}</div>}

          <a href={item.url.split('#')[0]} target="_blank" rel="noreferrer">
            <button className="btn">공고 원문 보기</button>
          </a>
          <div className="center-link"><button className="text-btn" onClick={onClose}>닫기</button></div>
        </>
      )}
    </BottomSheet>
  )
}
