import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { executeQuery, fetchSchema } from './api';
import type { DatabaseSchema, QueryRequest, QueryResponse } from './api';
import SearchableDropdown from './SearchableDropdown';

const DEFAULT_PAYLOAD = `{
  "username": "deep_testing",
  "city": "Gujarat",
  "family": [
      { "sister": "sis" },
      { "brother": "bro" }
  ]
}`;

const DEFAULT_UPDATES = `{
  "city": "Ahmedabad"
}`;

const KNOWN_SESSION_IDS = [
    'session_assignment_2',
    'session_test_01'
];

const TABLE_FALLBACK_ORDER = ['chiral_data', 'staging_data', 'session_metadata'];

type Operation = 'read' | 'create' | 'update' | 'delete';

interface ResultTab {
    id: number;
    label: string;
    response: QueryResponse;
    request: QueryRequest;
    timestamp: Date;
}
let tabCounter = 0;

const JsonCell: React.FC<{ data: unknown }> = ({ data }) => {
    const [expanded, setExpanded] = useState(false);

    if (typeof data !== 'object' || data === null) {
        return <>{String(data)}</>;
    }

    const jsonString = JSON.stringify(data, null, 2);
    const isLarge = jsonString.length > 40;

    if (!isLarge) {
        return <span className="jsonb-preview">{jsonString}</span>;
    }

    return (
        <div className="jsonb-cell">
            <button
                className="jsonb-toggle"
                onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            >
                {expanded ? '▲ Hide' : '▼ Show'} JSON
            </button>
            {!expanded && <span className="jsonb-preview">{"{...}"}</span>}
            {expanded && (
                <div className="jsonb-expanded">
                    {jsonString}
                </div>
            )}
        </div>
    );
};

interface CrudPanelProps {
    onDataChanged?: () => void;
}

const CrudPanel: React.FC<CrudPanelProps> = ({ onDataChanged }) => {
    const [operation, setOperation] = useState<Operation>('read');
    const [schema, setSchema] = useState<DatabaseSchema>({});
    const [, setFetchingSchema] = useState(true);

    const [sessionId, setSessionId] = useState('session_assignment_2');
    const [selectFields, setSelectFields] = useState<string>('');
    const [filterField, setFilterField] = useState('');
    const [filterOp, setFilterOp] = useState('eq');
    const [filterValue, setFilterValue] = useState('');
    const [limit, setLimit] = useState<number | string>(10);
    const [payloadJson, setPayloadJson] = useState(DEFAULT_PAYLOAD);
    const [updatesJson, setUpdatesJson] = useState(DEFAULT_UPDATES);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [resultTabs, setResultTabs] = useState<ResultTab[]>([]);
    const [activeTabId, setActiveTabId] = useState<number | null>(null);
    const [sidebarWidth, setSidebarWidth] = useState(380);

    useEffect(() => {
        let mounted = true;
        fetchSchema().then(liveSchema => {
            if (mounted) {
                setSchema(liveSchema);
                setFetchingSchema(false);
            }
        }).catch(err => {
            if (mounted) {
                setError("Failed to connect to backend: " + err.message);
                setFetchingSchema(false);
            }
        });
        return () => { mounted = false; };
    }, []);

    const tableList = useMemo(() => Object.keys(schema), [schema]);
    const columnOptions = useMemo(() => {
        const allColumns = new Set<string>();

        const parseObjectValue = (value: unknown): Record<string, unknown> | null => {
            if (value && typeof value === 'object' && !Array.isArray(value)) {
                return value as Record<string, unknown>;
            }
            if (typeof value === 'string') {
                try {
                    const parsed = JSON.parse(value) as unknown;
                    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                        return parsed as Record<string, unknown>;
                    }
                } catch {
                    return null;
                }
            }
            return null;
        };

        tableList.forEach(tableName => {
            const tableSchema = schema[tableName];
            tableSchema.columns.forEach(col => allColumns.add(col.name));

            const hasOverflowData = tableSchema.columns.some(col => col.name === 'overflow_data');
            if (!hasOverflowData || !tableSchema.sampleData) {
                return;
            }

            tableSchema.sampleData.forEach(sampleRow => {
                const parsedOverflow = parseObjectValue(sampleRow.overflow_data);
                if (!parsedOverflow) {
                    return;
                }

                Object.keys(parsedOverflow).forEach(key => {
                    allColumns.add(`overflow_data.${key}`);
                });
            });
        });
        return Array.from(allColumns).sort((a, b) => a.localeCompare(b));
    }, [schema, tableList]);

    const filterColumnOptions = useMemo(() => {
        return columnOptions.filter(c => c !== 'session_id');
    }, [columnOptions]);

    const inferTableFromMetadata = useCallback((fields: string[]) => {
        const cleanFields = Array.from(new Set(fields.map(f => f.trim()).filter(Boolean)));

        if (tableList.length === 0) {
            return { table: null as string | null, reason: 'Schema not loaded. Please retry in a moment.' };
        }

        if (cleanFields.length === 0) {
            const fallback = TABLE_FALLBACK_ORDER.find(t => tableList.includes(t)) || tableList[0];
            return { table: fallback, reason: '' };
        }

        const candidates = tableList.filter(tableName => {
            const cols = new Set(schema[tableName].columns.map(c => c.name));
            return cleanFields.every(field => {
                if (cols.has(field)) {
                    return true;
                }
                if (field.startsWith('overflow_data.')) {
                    return cols.has('overflow_data');
                }
                return false;
            });
        });

        if (candidates.length === 1) {
            return { table: candidates[0], reason: '' };
        }
        if (candidates.length === 0) {
            return {
                table: null as string | null,
                reason: `No table matches fields: ${cleanFields.join(', ')}`,
            };
        }

        const preferred = TABLE_FALLBACK_ORDER.find(t => candidates.includes(t));
        if (preferred) {
            return { table: preferred, reason: '' };
        }

        return {
            table: null as string | null,
            reason: `Ambiguous fields (${cleanFields.join(', ')}) match multiple tables: ${candidates.join(', ')}. Add a more specific field/filter.`,
        };
    }, [schema, tableList]);

    const startResize = useCallback((mouseDownEvent: React.MouseEvent) => {
        mouseDownEvent.preventDefault();
        const startX = mouseDownEvent.clientX;
        const startWidth = sidebarWidth;

        const onMouseMove = (moveEvent: MouseEvent) => {
            let newWidth = startWidth + (moveEvent.clientX - startX);
            if (newWidth < 250) newWidth = 250;
            if (newWidth > 800) newWidth = 800;
            setSidebarWidth(newWidth);
        };
        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }, [sidebarWidth]);

    const executeOp = useCallback(async () => {
        setError(null);
        setLoading(true);

        const selectedReadFields = selectFields
            ? selectFields.split(',').map(s => s.trim()).filter(Boolean)
            : [];

        if (operation === 'read' && selectedReadFields.length === 0) {
            setError('Please enter required fields in Select Fields.');
            setLoading(false);
            return;
        }

        const hasFilterField = filterField.trim().length > 0;
        const hasFilterValue = filterValue.trim().length > 0;
        const hasFullFilter = hasFilterField && hasFilterValue;

        if (operation === 'read' && (hasFilterField !== hasFilterValue)) {
            setError('Please provide both filter field and value, or leave both empty.');
            setLoading(false);
            return;
        }

        const inferredFields: string[] = [];

        if (operation === 'read') {
            inferredFields.push(...selectedReadFields);
        }
        if (hasFullFilter) {
            inferredFields.push(filterField);
        }
        if (operation === 'create') {
            try {
                const parsedPayload = JSON.parse(payloadJson) as Record<string, unknown>;
                inferredFields.push(...Object.keys(parsedPayload));
            } catch {
                setError('Invalid JSON payload for CREATE');
                setLoading(false);
                return;
            }
        }
        if (operation === 'update') {
            try {
                const parsedUpdates = JSON.parse(updatesJson) as Record<string, unknown>;
                inferredFields.push(...Object.keys(parsedUpdates));
            } catch {
                setError('Invalid JSON payload for UPDATE');
                setLoading(false);
                return;
            }
        }

        const inferred = inferTableFromMetadata(inferredFields);
        if (!inferred.table) {
            setError(inferred.reason);
            setLoading(false);
            return;
        }

        const req: QueryRequest = { operation, table: inferred.table };
        if (sessionId) req.session_id = sessionId;

        if (operation === 'read') {
            req.select = selectedReadFields;
            if (limit) {
                req.limit = typeof limit === 'string' ? parseInt(limit, 10) : limit;
            }
        }

        if (hasFullFilter) {
            let val: string | number | boolean = filterValue;
            if (!isNaN(Number(val)) && typeof val === 'string' && val.trim() !== '') {
                val = Number(val);
            } else if (typeof val === 'string' && val.toLowerCase() === 'true') {
                val = true;
            } else if (typeof val === 'string' && val.toLowerCase() === 'false') {
                val = false;
            }
            req.filters = [{ field: filterField, operator: filterOp, value: val }];
        }

        if (operation === 'create') {
            req.payload = JSON.parse(payloadJson);
        }

        if (operation === 'update') {
            req.updates = JSON.parse(updatesJson);
        }

        try {
            const response = await executeQuery(req);
            const resolvedTable = req.table || 'unknown_table';
            const tabLabel = `${operation.toUpperCase()} ${resolvedTable.split('_').slice(0, 2).join('_')}`;

            setResultTabs(prev => {
                const existingIdx = prev.findIndex(t => t.label === tabLabel);
                if (existingIdx >= 0) {
                    const updated = [...prev];
                    updated[existingIdx] = {
                        ...updated[existingIdx],
                        response,
                        request: req,
                        timestamp: new Date()
                    };
                    setTimeout(() => setActiveTabId(updated[existingIdx].id), 0);
                    return updated;
                } else {
                    const newTab: ResultTab = {
                        id: ++tabCounter,
                        label: tabLabel,
                        response,
                        request: req,
                        timestamp: new Date(),
                    };
                    setTimeout(() => setActiveTabId(newTab.id), 0);
                    return [...prev, newTab];
                }
            });

            if (operation !== 'read' && onDataChanged) {
                onDataChanged();
                fetchSchema().then(setSchema).catch(console.error);
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Unknown error';
            setError(msg);
        } finally {
            setLoading(false);
        }
    }, [operation, sessionId, selectFields, filterField, filterOp, filterValue, payloadJson, updatesJson, limit, onDataChanged, inferTableFromMetadata]);

    const activeTab = resultTabs.find(t => t.id === activeTabId);

    return (
        <div className="crud-panel">
            <div className="crud-form-container" style={{ width: sidebarWidth }}>
                <div className="crud-resizer" onMouseDown={startResize} />
                <div className="crud-form">
                    <h2 className="crud-title">Query Executor</h2>

                    <div className="crud-row">
                        <label>Operation</label>
                        <div className="crud-op-selector">
                            {(['read', 'create', 'update', 'delete'] as Operation[]).map(op => (
                                <button
                                    key={op}
                                    className={`crud-op-btn ${operation === op ? 'active' : ''} crud-op-${op}`}
                                    onClick={() => setOperation(op)}
                                >
                                    {op === 'read' && '▶ '}
                                    {op === 'create' && '+ '}
                                    {op === 'update' && '✎ '}
                                    {op === 'delete' && '🗑 '}
                                    {op.toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="crud-row">
                        <label>Table</label>
                        <div className="crud-input" style={{ opacity: 0.8 }}>
                            Auto-detected from schema metadata using selected fields and filter.
                        </div>
                    </div>

                    <div className="crud-row">
                        <label>Session ID</label>
                        <SearchableDropdown
                            options={KNOWN_SESSION_IDS}
                            value={sessionId}
                            onChange={setSessionId}
                            placeholder="Type or select session..."
                            allowFreeText
                        />
                    </div>

                    {operation === 'read' && (
                        <>
                            <div className="crud-row">
                                <label>Select Fields</label>
                                <SearchableDropdown
                                    options={columnOptions}
                                    value={selectFields}
                                    onChange={setSelectFields}
                                    placeholder="Type column names (comma separated)..."
                                    allowFreeText
                                    multiple
                                />
                            </div>
                            <div className="crud-row">
                                <label>Limit</label>
                                <input className="crud-input" type="number" value={limit} onChange={e => setLimit(e.target.value)} />
                            </div>
                        </>
                    )}

                    <div className="crud-row">
                        <label>Filter</label>
                        <div className="crud-filter-row">
                            <SearchableDropdown
                                options={filterColumnOptions}
                                value={filterField}
                                onChange={setFilterField}
                                placeholder="field"
                                allowFreeText
                            />
                            <select value={filterOp} onChange={e => setFilterOp(e.target.value)} className="crud-select crud-select-sm">
                                <option value="eq">=</option>
                                <option value="neq">≠</option>
                                <option value="gt">&gt;</option>
                                <option value="lt">&lt;</option>
                                <option value="gte">≥</option>
                                <option value="lte">≤</option>
                                <option value="like">LIKE</option>
                            </select>
                            <input className="crud-input crud-input-sm" value={filterValue} onChange={e => setFilterValue(e.target.value)} placeholder="value" />
                        </div>
                    </div>

                    {operation === 'create' && (
                        <div className="crud-row">
                            <label>Payload (JSON)</label>
                            <textarea
                                className="crud-textarea"
                                value={payloadJson}
                                onChange={e => {
                                    setPayloadJson(e.target.value);
                                    e.target.style.height = 'auto';
                                    e.target.style.height = e.target.scrollHeight + 'px';
                                }}
                                ref={el => {
                                    if (el) {
                                        el.style.height = 'auto';
                                        el.style.height = el.scrollHeight + 'px';
                                    }
                                }}
                            />
                        </div>
                    )}

                    {operation === 'update' && (
                        <div className="crud-row">
                            <label>Updates (JSON)</label>
                            <textarea
                                className="crud-textarea"
                                value={updatesJson}
                                onChange={e => {
                                    setUpdatesJson(e.target.value);
                                    e.target.style.height = 'auto';
                                    e.target.style.height = e.target.scrollHeight + 'px';
                                }}
                                ref={el => {
                                    if (el) {
                                        el.style.height = 'auto';
                                        el.style.height = el.scrollHeight + 'px';
                                    }
                                }}
                            />
                        </div>
                    )}

                    <button className="crud-submit-btn" onClick={executeOp} disabled={loading}>
                        {loading ? 'Executing...' : (
                            <>
                                {operation === 'read' && '▶ '}
                                {operation === 'create' && '+ '}
                                {operation === 'update' && '✎ '}
                                {operation === 'delete' && '🗑 '}
                                Execute {operation.toUpperCase()}
                            </>
                        )}
                    </button>
                </div>
            </div>

            <div className="crud-results">
                {error && (
                    <div className="crud-error-banner">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="12" y1="8" x2="12" y2="12" />
                            <line x1="12" y1="16" x2="12.01" y2="16" />
                        </svg>
                        {error}
                        <button className="crud-error-dismiss" onClick={() => setError(null)}>✕</button>
                    </div>
                )}

                <div className="crud-tabs-header">
                    {resultTabs.length === 0 ? (
                        <div className="crud-tabs-empty">No results yet. Run a query.</div>
                    ) : (
                        resultTabs.map(tab => (
                            <div
                                key={tab.id}
                                className={`crud-tab ${activeTabId === tab.id ? 'active' : ''}`}
                                onClick={() => setActiveTabId(tab.id)}
                            >
                                <span className={`crud-tab-indicator op-${tab.label.split(' ')[0].toLowerCase()}`} />
                                {tab.label}
                                <span className="crud-tab-close" onClick={(e) => {
                                    e.stopPropagation();
                                    setResultTabs(prev => prev.filter(t => t.id !== tab.id));
                                    if (activeTabId === tab.id) {
                                        setActiveTabId(resultTabs.length > 1 ? resultTabs[resultTabs.length - 2].id : null);
                                    }
                                }}>
                                    ✕
                                </span>
                            </div>
                        ))
                    )}
                </div>

                {activeTab ? (
                    <div className="crud-tab-content crud-result-view">
                        <div className="crud-result-meta">
                            <span className="crud-result-time">⏱ {activeTab.timestamp.toLocaleTimeString()}</span>
                            {activeTab.response.row_count !== undefined && (
                                <span className="crud-result-badge crud-result-count">{activeTab.response.row_count} rows read/affected</span>
                            )}
                            {activeTab.response.affected_rows !== undefined && (
                                <span className="crud-result-badge">{activeTab.response.affected_rows} rows written</span>
                            )}
                            {activeTab.response.mode === 'queued_async' && (
                                <span className="crud-result-badge">QUEUED ASYNC</span>
                            )}
                        </div>

                        <div className="crud-sql-block">
                            <pre>{activeTab.response.sql || '-- No SQL executed (handled via background staging queue)'}</pre>
                        </div>

                        {activeTab.response.rows && activeTab.response.rows.length > 0 && (
                            <div className="crud-data-scroll">
                                <table className="crud-data-table">
                                    <thead>
                                        <tr>
                                            {Object.keys(activeTab.response.rows[0]).map(k => (
                                                <th key={k}>{k}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {activeTab.response.rows.map((row: Record<string, unknown>, i: number) => (
                                            <tr key={i}>
                                                {Object.keys(activeTab.response.rows![0]).map(k => (
                                                    <td key={k}>
                                                        {typeof row[k] === 'object' ? <JsonCell data={row[k]} /> : String(row[k])}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {(activeTab.response.params && Object.keys(activeTab.response.params).length > 0) && (
                            <div className="crud-sql-block" style={{ marginTop: '12px' }}>
                                <pre>{JSON.stringify(activeTab.response.params, null, 2)}</pre>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="crud-tab-content-empty">
                        Execute an operation to see results.
                    </div>
                )}
            </div>
        </div>
    );
};

export default CrudPanel;
