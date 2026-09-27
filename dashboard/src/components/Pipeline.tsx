const STEPS = [
  {
    num: '01',
    title: 'Bob works',
    hook: 'PostToolUse',
    desc: 'Every tool call is hash-chained into a tamper-evident trace log.',
  },
  {
    num: '02',
    title: 'Bob says done',
    hook: 'Stop',
    desc: "The verdict engine runs independent tests, checks test integrity, and validates the agent's claim.",
  },
  {
    num: '03',
    title: 'Bob tries to commit',
    hook: 'PreToolUse',
    desc: 'The gate intercepts git commit / push. Unproven claims exit 2 and block the command.',
  },
  {
    num: '04',
    title: 'Bob gets feedback',
    hook: 'UserPromptSubmit',
    desc: 'Missing evidence is injected into the next prompt so the agent knows exactly what to fix.',
  },
]

export default function Pipeline() {
  return (
    <div className="pipeline">
      {STEPS.map((step, i) => (
        <>
          <div key={step.num} className="pipeline-step">
            <div className="pipeline-step__num">STEP {step.num}</div>
            <div className="pipeline-step__title">{step.title}</div>
            <div className="pipeline-step__hook">{step.hook}</div>
            <div className="pipeline-step__desc">{step.desc}</div>
          </div>
          {i < STEPS.length - 1 && (
            <div key={`arrow-${i}`} className="pipeline-arrow">›</div>
          )}
        </>
      ))}
    </div>
  )
}
