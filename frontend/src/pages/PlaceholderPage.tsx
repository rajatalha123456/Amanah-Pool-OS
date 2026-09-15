import { Card } from "../components/Card"
import { PageHeader } from "../components/PageHeader"

interface PlaceholderPageProps {
  title: string
}

export function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <div>
      <PageHeader title={title} />
      <Card>
        <p className="text-sm text-ink-secondary">
          Content for {title} will be added here.
        </p>
      </Card>
    </div>
  )
}
