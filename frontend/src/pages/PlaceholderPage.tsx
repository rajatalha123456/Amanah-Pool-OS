import { Card } from "../components/Card"

interface PlaceholderPageProps {
  title: string
}

export function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold text-white">{title}</h1>
      <Card>
        <p className="text-sm text-gray-400">
          Content for {title} will be added here.
        </p>
      </Card>
    </div>
  )
}
