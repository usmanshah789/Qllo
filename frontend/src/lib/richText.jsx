// The agent writes plain prose with **bold** names and the odd "- " list.
// A full markdown renderer would be more than this needs.
function inline(text, keyPrefix) {
  // Built per call: a shared /g regex keeps lastIndex between paragraphs and
  // starts matching halfway through the next one.
  const bold = /\*\*([^*]+)\*\*/g
  const parts = []
  let last = 0
  let match
  while ((match = bold.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    parts.push(
      <strong key={`${keyPrefix}-${match.index}`} className="font-medium text-neutral-50">
        {match[1]}
      </strong>,
    )
    last = match.index + match[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts.map((part) => (typeof part === 'string' ? part.replace(/\*/g, '') : part))
}

export function RichText({ text }) {
  const blocks = text.split('\n').filter((line) => line.trim() !== '')

  return (
    <div className="space-y-2.5">
      {blocks.map((line, i) => {
        const bullet = line.trimStart().startsWith('- ')
        const body = bullet ? line.trimStart().slice(2) : line
        return (
          <p
            key={i}
            className={bullet ? 'relative pl-4 before:absolute before:left-0 before:text-neutral-600 before:content-["—"]' : ''}
          >
            {inline(body, i)}
          </p>
        )
      })}
    </div>
  )
}
