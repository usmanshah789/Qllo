import EntityCard from './EntityCard'
import { RichText } from '../lib/richText'

export default function Message({ message, onDislike }) {
  if (message.role === 'user') {
    return (
      <div className="rise flex justify-end">
        <div className="user-bubble max-w-[80%] rounded-2xl rounded-br-md px-4 py-2.5 text-sm text-neutral-100">
          {message.content}
        </div>
      </div>
    )
  }

  const cards = message.recommendations ?? []

  return (
    <div className="rise space-y-3">
      <div className="panel max-w-[88%] rounded-2xl rounded-bl-md px-4 py-3 text-sm leading-relaxed text-neutral-300">
        <RichText text={message.content} />
      </div>

      {cards.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {cards.map((rec) => (
            <EntityCard key={rec.entity.id} entity={rec.entity} onDislike={onDislike} />
          ))}
        </div>
      )}
    </div>
  )
}
