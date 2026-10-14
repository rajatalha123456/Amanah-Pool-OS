ROOT = "frontend/src/"


def edit(path, pairs):
    s = open(ROOT + path, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:90])
        s = s.replace(old, new, 1)
    open(ROOT + path, "w", encoding="utf-8").write(s)


# ---- API functions return a page ----------------------------------------------------------------
edit("api/auditLog.ts", [
    ('import { apiClient } from "./axios"\n', 'import { apiClient } from "./axios"\nimport { pageParams, type Page } from "./pagination"\n'),
    ('''export async function fetchAuditLogs(params: FetchAuditLogParams = {}): Promise<AuditLogEntry[]> {
  const response = await apiClient.get<AuditLogEntry[]>("core/audit-log/", { params })
  return response.data
}''', '''export async function fetchAuditLogs(params: FetchAuditLogParams = {}, page = 1): Promise<Page<AuditLogEntry>> {
  const response = await apiClient.get<Page<AuditLogEntry>>("core/audit-log/", { params: { ...params, ...pageParams(page) } })
  return response.data
}'''),
])
edit("api/notifications.ts", [
    ('import { apiClient } from "./axios"\n', 'import { apiClient } from "./axios"\nimport { pageParams, type Page } from "./pagination"\n'),
    ('''export async function fetchNotifications(params?: { unread?: boolean; category?: string }): Promise<AppNotification[]> {
  const response = await apiClient.get<AppNotification[]>("notifications/", {
    params: { ...(params?.unread ? { unread: "true" } : {}), ...(params?.category ? { category: params.category } : {}) },
  })
  return response.data
}''', '''export async function fetchNotifications(
  params?: { unread?: boolean; category?: string },
  page = 1,
  pageSize?: number,
): Promise<Page<AppNotification>> {
  const response = await apiClient.get<Page<AppNotification>>("notifications/", {
    params: {
      ...(params?.unread ? { unread: "true" } : {}),
      ...(params?.category ? { category: params.category } : {}),
      ...pageParams(page, pageSize),
    },
  })
  return response.data
}'''),
])
edit("api/participants.ts", [
    ('import { apiClient } from "./axios"\n', 'import { apiClient } from "./axios"\nimport { pageParams, type Page } from "./pagination"\n'),
    ('''export async function fetchParticipants(): Promise<Participant[]> {
  const response = await apiClient.get<Participant[]>("participants/participants/")
  return response.data
}

export async function fetchParticipantAccounts(poolId?: string): Promise<ParticipantAccount[]> {
  const response = await apiClient.get<ParticipantAccount[]>("participants/accounts/", {
    params: poolId ? { pool: poolId } : undefined,
  })
  return response.data
}''', '''export async function fetchParticipants(page = 1): Promise<Page<Participant>> {
  const response = await apiClient.get<Page<Participant>>("participants/participants/", { params: pageParams(page) })
  return response.data
}

/** Accounts of the given participants (one page of the registry), at most 500. */
export async function fetchAccountsOfParticipants(participantIds: string[]): Promise<ParticipantAccount[]> {
  if (participantIds.length === 0) return []
  const response = await apiClient.get<Page<ParticipantAccount>>("participants/accounts/", {
    params: { participants: participantIds.join(","), ...pageParams(1, 500) },
  })
  return response.data.results
}'''),
])
edit("api/accounting.ts", [
    ('import { apiClient } from "./axios"\n', 'import { apiClient } from "./axios"\nimport { pageParams, type Page } from "./pagination"\n'),
    ('''export async function fetchJournalBatches(poolId: string): Promise<JournalBatch[]> {
  const response = await apiClient.get<JournalBatch[]>("accounting/journal-batches/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchIncomeExpenseEvents(poolId?: string): Promise<IncomeExpenseEvent[]> {
  const response = await apiClient.get<IncomeExpenseEvent[]>("accounting/income-expense-events/", {
    params: poolId ? { pool: poolId } : undefined,
  })
  return response.data
}''', '''export async function fetchJournalBatches(poolId: string, page = 1): Promise<Page<JournalBatch>> {
  const response = await apiClient.get<Page<JournalBatch>>("accounting/journal-batches/", {
    params: { pool: poolId, ...pageParams(page) },
  })
  return response.data
}

export async function fetchIncomeExpenseEvents(poolId?: string, page = 1): Promise<Page<IncomeExpenseEvent>> {
  const response = await apiClient.get<Page<IncomeExpenseEvent>>("accounting/income-expense-events/", {
    params: { ...(poolId ? { pool: poolId } : {}), ...pageParams(page) },
  })
  return response.data
}'''),
])
edit("api/balances.ts", [
    ('import { apiClient } from "./axios"\n', 'import { apiClient } from "./axios"\nimport { pageParams, type Page } from "./pagination"\n'),
    ('''export async function fetchDailyBalances(poolId: string, valueDate: string): Promise<DailyBalance[]> {
  const response = await apiClient.get<DailyBalance[]>("pools/daily-balances/", {
    params: { pool: poolId, value_date: valueDate },
  })
  return response.data
}''', '''export async function fetchDailyBalances(poolId: string, valueDate: string, page = 1): Promise<Page<DailyBalance>> {
  const response = await apiClient.get<Page<DailyBalance>>("pools/daily-balances/", {
    params: { pool: poolId, value_date: valueDate, ...pageParams(page) },
  })
  return response.data
}'''),
])

# ---- Auditor portal --------------------------------------------------------------------------------
edit("pages/AuditorPortal.tsx", [
    ("  const [entries, setEntries] = useState<AuditLogEntry[]>([])\n",
     "  const [entries, setEntries] = useState<AuditLogEntry[]>([])\n  const [logPage, setLogPage] = useState(1)\n  const [logCount, setLogCount] = useState(0)\n"),
    ('''  function loadEntries() {
    setIsLoading(true)
    setPageError("")
    fetchAuditLog({
      model_name: modelName || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then((data: AuditLogEntry[]) => setEntries(data))''', '''  function loadEntries(page = 1) {
    setIsLoading(true)
    setPageError("")
    fetchAuditLog(
      {
        model_name: modelName || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      },
      page,
    )
      .then((data) => {
        setEntries(data.results)
        setLogCount(data.count)
        setLogPage(page)
      })'''),
    ('''            <Table columns={columns} data={entries} keyField={(entry) => entry.id} />
          )}''', '''            <>
              <Table columns={columns} data={entries} keyField={(entry) => entry.id} />
              <Pager page={logPage} pageSize={DEFAULT_PAGE_SIZE} count={logCount} onChange={loadEntries} disabled={isLoading} />
            </>
          )}'''),
    ('import { downloadAuditLogCsv, fetchAuditLog } from "../api/auditLog"\n',
     'import { downloadAuditLogCsv, fetchAuditLog } from "../api/auditLog"\nimport { DEFAULT_PAGE_SIZE } from "../api/pagination"\nimport { Pager } from "../components/Pager"\n'),
])

# ---- Security audit log (administration) ----------------------------------------------------------------
edit("pages/administration/SecurityAuditLog.tsx", [
    ("  const [logs, setLogs] = useState<AuditLogEntry[]>([])\n",
     "  const [logs, setLogs] = useState<AuditLogEntry[]>([])\n  const [page, setPage] = useState(1)\n  const [count, setCount] = useState(0)\n"),
    ('''  const loadLogs = async () => {
    setLoading(true)
    setError("")
    try {
      const data = await fetchAuditLogs({
        model_name: modelFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      })
      setLogs(data)''', '''  const loadLogs = async (toPage = 1) => {
    setLoading(true)
    setError("")
    try {
      const data = await fetchAuditLogs(
        {
          model_name: modelFilter || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        },
        toPage,
      )
      setLogs(data.results)
      setCount(data.count)
      setPage(toPage)'''),
    ('''          <Table
            columns={columns}
            data={filteredLogs}
            keyField={(log) => log.id}
          />
        )}''', '''          <>
            <Table
              columns={columns}
              data={filteredLogs}
              keyField={(log) => log.id}
            />
            <Pager page={page} pageSize={DEFAULT_PAGE_SIZE} count={count} onChange={(p) => void loadLogs(p)} disabled={loading} />
          </>
        )}'''),
    ('import { fetchAuditLogs, exportAuditLogsCsv } from "../../api/auditLog"\n',
     'import { fetchAuditLogs, exportAuditLogsCsv } from "../../api/auditLog"\nimport { DEFAULT_PAGE_SIZE } from "../../api/pagination"\nimport { Pager } from "../../components/Pager"\n'),
])

# ---- Participants ------------------------------------------------------------------------------------
edit("pages/ParticipantRegistry.tsx", [
    ("  fetchParticipantAccounts,\n  fetchParticipants,\n", "  fetchAccountsOfParticipants,\n  fetchParticipants,\n"),
    ("  const [accounts, setAccounts] = useState<ParticipantAccount[]>([])\n",
     "  const [accounts, setAccounts] = useState<ParticipantAccount[]>([])\n  const [page, setPage] = useState(1)\n  const [count, setCount] = useState(0)\n"),
    ('''  const load = useCallback(async () => {
    try {
      const [p, a] = await Promise.all([fetchParticipants(), fetchParticipantAccounts()])
      setParticipants(p)
      setAccounts(a)
      setError("")''', '''  const load = useCallback(async () => {
    try {
      const p = await fetchParticipants(page)
      setParticipants(p.results)
      setCount(p.count)
      setAccounts(await fetchAccountsOfParticipants(p.results.map((x) => x.id)))
      setError("")'''),
    ("  }, [])\n\n  useEffect(() => {\n    void load()\n  }, [load])", "  }, [page])\n\n  useEffect(() => {\n    void load()\n  }, [load])"),
    ('<Card title={`Participant Registry (${participants.length})`}>', '<Card title={`Participant Registry (${count})`}>'),
    ('''          <Table columns={columns} data={participants} keyField={(p) => p.id} />
        )}''', '''          <>
            <Table columns={columns} data={participants} keyField={(p) => p.id} />
            <Pager page={page} pageSize={DEFAULT_PAGE_SIZE} count={count} onChange={setPage} />
          </>
        )}'''),
])

# ---- Journal batches ---------------------------------------------------------------------------------
edit("pages/JournalBatchReview.tsx", [
    ("  const [batches, setBatches] = useState<JournalBatch[]>([])\n",
     "  const [batches, setBatches] = useState<JournalBatch[]>([])\n  const [page, setPage] = useState(1)\n  const [count, setCount] = useState(0)\n"),
    ('''    fetchJournalBatches(selectedPoolId)
      .then((data) => {
        setBatches(data)
        setPageState("loaded")''', '''    fetchJournalBatches(selectedPoolId, page)
      .then((data) => {
        setBatches(data.results)
        setCount(data.count)
        setPageState("loaded")'''),
    ("  }, [selectedPoolId])\n", "  }, [selectedPoolId, page])\n"),
    ('''            })}
          </div>
        )}
      </Card>
''', '''            })}
            <Pager page={page} pageSize={DEFAULT_PAGE_SIZE} count={count} onChange={setPage} />
          </div>
        )}
      </Card>
'''),
    ('        {batches.length} batch{batches.length === 1 ? "" : "es"} · debits',
     '        {count > batches.length ? `This page: ${batches.length} of ${count} batches` : `${batches.length} batch${batches.length === 1 ? "" : "es"}`} · debits'),
    ('import { fetchJournalBatches } from "../api/accounting"\n',
     'import { fetchJournalBatches } from "../api/accounting"\nimport { DEFAULT_PAGE_SIZE } from "../api/pagination"\nimport { Pager } from "../components/Pager"\n'),
])

# ---- Income and expense -------------------------------------------------------------------------------
edit("pages/IncomeExpenseWorkbench.tsx", [
    ("  const [events, setEvents] = useState<IncomeExpenseEvent[]>([])\n",
     "  const [events, setEvents] = useState<IncomeExpenseEvent[]>([])\n  const [eventPage, setEventPage] = useState(1)\n  const [eventCount, setEventCount] = useState(0)\n"),
    ('''  async function loadData(poolId: string) {
    if (!poolId) return''', '''  async function loadData(poolId: string, page = eventPage) {
    if (!poolId) return'''),
    ('''        fetchIncomeExpenseEvents(poolId),
        fetchPoolIncomeExpenseSummary(poolId),
      ])
      setEvents(eventsData)''', '''        fetchIncomeExpenseEvents(poolId, page),
        fetchPoolIncomeExpenseSummary(poolId),
      ])
      setEvents(eventsData.results)
      setEventCount(eventsData.count)
      setEventPage(page)'''),
    ("            All Items ({events.length})", "            All Items ({eventCount})"),
    ('''            </table>
          </div>
        )}
      </Card>
''', '''            </table>
            <Pager page={eventPage} pageSize={DEFAULT_PAGE_SIZE} count={eventCount} onChange={(p) => void loadData(selectedPoolId, p)} disabled={isLoading} />
          </div>
        )}
      </Card>
'''),
    ('import { fetchPools } from "../api/pools"\n',
     'import { fetchPools } from "../api/pools"\nimport { DEFAULT_PAGE_SIZE } from "../api/pagination"\nimport { Pager } from "../components/Pager"\n'),
])

# ---- Notifications ---------------------------------------------------------------------------------
edit("pages/Notifications.tsx", [
    ("  const [items, setItems] = useState<AppNotification[]>([])\n",
     "  const [items, setItems] = useState<AppNotification[]>([])\n  const [page, setPage] = useState(1)\n  const [count, setCount] = useState(0)\n"),
    ('''      setItems(await fetchNotifications({ unread: onlyUnread }))
      setError("")''', '''      const data = await fetchNotifications({ unread: onlyUnread }, page)
      setItems(data.results)
      setCount(data.count)
      setError("")'''),
    ("  }, [onlyUnread])\n", "  }, [onlyUnread, page])\n"),
    ('<Card title={`Inbox (${items.length})`}>', '<Card title={`Inbox (${count})`}>'),
    ('''            ))}
          </ul>
        )}
      </Card>''', '''            ))}
          </ul>
        )}
        <Pager page={page} pageSize={DEFAULT_PAGE_SIZE} count={count} onChange={setPage} disabled={loading} />
      </Card>'''),
])
edit("components/NotificationBell.tsx", [
    ("        setItems((await fetchNotifications({ unread: true })).slice(0, 8))",
     "        setItems((await fetchNotifications({ unread: true }, 1, 8)).results)"),
])
print("ok")
