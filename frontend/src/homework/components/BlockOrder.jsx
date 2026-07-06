import React from 'react'
import { GripVertical } from 'lucide-react'
import { KoreanWithRomanization } from '../utils/koreanText.jsx'

export default function BlockOrder({ blocks, selected, onChange, disabled, dialogue = false }) {
  function addBlock(block, index) {
    if (disabled) return
    onChange([...selected, block], index)
  }

  function removeBlock(index) {
    if (disabled) return
    onChange(selected.filter((_, selectedIndex) => selectedIndex !== index))
  }

  return (
    <div className={`block-order ${dialogue ? 'dialogue-order' : ''}`}>
      <div className="answer-tray" aria-label="Selected answer">
        {selected.length === 0 ? (
          <span
            className="placeholder"
            style={{ '--placeholder-columns': Math.max(blocks.length, 1) }}
          >
            {blocks.map((_, index) => <i key={index}>{index + 1}</i>)}
          </span>
        ) : null}
        {selected.map((block, index) => (
          <button className="pill selected" key={`${block}-${index}`} onClick={() => removeBlock(index)} type="button">
            {dialogue ? <span className="dialogue-index">{index + 1}</span> : null}
            <KoreanWithRomanization text={block} />
          </button>
        ))}
      </div>
      <div className="block-bank" aria-label="Available blocks">
        {blocks.map((block, index) => {
          const usedCount = selected.filter((item) => item === block).length
          const totalBefore = blocks.slice(0, index + 1).filter((item) => item === block).length
          const isUsed = usedCount >= totalBefore
          return (
            <button className="pill" disabled={disabled || isUsed} key={`${block}-${index}`} onClick={() => addBlock(block, index)} type="button">
              {dialogue ? <GripVertical size={22} /> : null}
              <KoreanWithRomanization text={block} />
            </button>
          )
        })}
      </div>
    </div>
  )
}
