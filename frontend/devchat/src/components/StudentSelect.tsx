import type { DemoStudent } from '../lib/api.ts'

interface Props {
  students: DemoStudent[]
  selected: string
  onSelect: (id: string) => void
  onReset: () => void
}

export function StudentSelect({ students, selected, onSelect, onReset }: Props) {
  return (
    <div className="student-bar">
      <label htmlFor="student-select" className="student-label">학생 선택</label>
      <select
        id="student-select"
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
        className="student-select"
      >
        {students.length === 0 && (
          <option value="">로딩 중...</option>
        )}
        {students.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name} ({s.visa_type}, {s.school})
          </option>
        ))}
      </select>
      <button type="button" onClick={onReset} className="reset-btn">
        대화 리셋
      </button>
    </div>
  )
}
