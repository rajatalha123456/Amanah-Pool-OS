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
    <div className="overflow-x-auto rounded-lg border border-navy-700">
      <table className="min-w-full divide-y divide-navy-700 text-sm">
        <thead className="bg-navy-800">
          <tr>
            {columns.map((col) => (
              <th
                key={col.header}
                className="px-4 py-3 text-left font-semibold tracking-wide text-gray-300 uppercase"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-navy-800 bg-navy-900">
          {data.map((row) => (
            <tr key={keyField(row)} className="hover:bg-navy-800/60">
              {columns.map((col) => (
                <td key={col.header} className="px-4 py-3 text-gray-200">
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
