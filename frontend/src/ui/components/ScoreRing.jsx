export default function ScoreRing({ score, size = 56 }) {
  const r = (size - 8) / 2
  const circumference = 2 * Math.PI * r
  const progress = circumference - (score / 100) * circumference

  return (
    <div style={{ width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="var(--color-border)" strokeWidth="4"
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="var(--color-accent)" strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={progress}
          strokeLinecap="round"
        />
      </svg>
      <div style={{
        position: 'relative',
        top: `-${size}px`,
        height: `${size}px`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <span style={{ fontSize: size * 0.25, fontWeight: 700, color: 'var(--color-ink)', fontFamily: 'var(--font-display)', lineHeight: 1 }}>{score}</span>
        <span style={{ fontSize: size * 0.16, color: 'var(--color-muted)', lineHeight: 1 }}>AI</span>
      </div>
    </div>
  )
}
