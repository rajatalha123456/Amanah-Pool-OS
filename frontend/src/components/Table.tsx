import type { ReactNode } from "react"

export interface TableColumn<T> {
  header: string
  accessor: (row: T) => ReactNode
}

interface TableProps<T> {
  columns: TableColumn<T>[]
  data: T[]
  keyField: (row: T) => string | number
}

export function Table<T>({ columns, data, keyField }: TableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/8">
      <table className="min-w-full text-sm">
        <thead className="bg-navy-800">
          <tr>
            {columns.map((col) => (
              <th
                key={col.header}
                className="px-4 py-3 text-left text-xs font-semibold tracking-wide text-ink-secondary uppercase"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5 bg-navy-900">
          {data.map((row) => (
            <tr key={keyField(row)} className="transition-colors hover:bg-white/[0.03]">
              {columns.map((col) => (
                <td key={col.header} className="px-4 py-3 text-ink-primary">
                  {col.accessor(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
