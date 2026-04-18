import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { executeQuery, fetchLogicalFields, fetchSessions, fetchSessionInfo } from './api';
import type { QueryRequest, QueryResponse, SessionInfo } from './api';
import SearchableDropdown from './SearchableDropdown';

const DEFAULT_PAYLOAD = `{
  "username": "deep_testing",
  "city": "Gujarat",
  "comments":[
      { "text": "hello" }
  ]
}`;

type Operation = 'read' | 'create' | 'update' | 'delete';

interface FilterInput {
    field: string;
    op: string;
    value: string;
}

interface ResultTab {
    id: number;
    label: string;
    response: QueryResponse;
    request: QueryRequest;
    timestamp: Date;
}

interface InspectorNode {
    name: string;
    path: string;
    children: InspectorNode[];
}

type InspectorTree = Record<string, unknown>;

function buildInspectorTree(fields: string[]): InspectorNode[] {
    const root: InspectorTree = {};

    for (const field of fields) {
        const parts = field.split('.').filter(Boolean);
        if (parts.length === 0) continue;
        let node: InspectorTree = root;
        for (const part of parts) {
            if (!node[part] || typeof node[part] !== 'object') {
                node[part] = {};
            }
            node = node[part] as InspectorTree;
        }
    }

    const toNodes = (tree: InspectorTree, parentPath = ''): InspectorNode[] => {
        return Object.keys(tree)
            .sort((a, b) => a.localeCompare(b))
            .map((name) => {
                const path = parentPath ? `${parentPath}.${name}` : name;
                return {
                    name,
                    path,
                    children: toNodes(tree[name] as InspectorTree, path),
                };
            });
    };

    return toNodes(root);
}

let tabCounter = 0;

const JsonCell: React.FC<{ data: unknown }> = ({ data }) => {
    const[expanded, setExpanded] = useState(false);
    if (typeof data !== 'object' || data === null) return <>{String(data)}</>;
    const jsonString = JSON.stringify(data, null, 2);
    if (jsonString.length <= 40) return <span className="jsonb-preview">{jsonString}</span>;
    return (
        <div className="jsonb-cell">
            <button className="jsonb-toggle" onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}>
                {expanded ? '▲ Hide' : '▼ Show'} JSON
            </button>
            {!expanded && <span className="jsonb-preview">{"{...}"}</span>}
            {expanded && <div className="jsonb-expanded">{jsonString}</div>}
        </div>
    );
};

function buildGroupedSelectOptions(fields: string[]): { options: string[]; details: Record<string, string[]> } {
    const options: string[] = [];
    const details: Record<string, string[]> = {};
    const optionSet = new Set<string>();

    for (const field of fields) {
        if (!field.includes('.')) {
            if (!optionSet.has(field)) {
                optionSet.add(field);
                options.push(field);
            }
            continue;
        }

        const [parent, ...restParts] = field.split('.');
        const child = restParts.join('.');
        if (!optionSet.has(parent)) {
            optionSet.add(parent);
            options.push(parent);
        }

        if (!details[parent]) {
            details[parent] = [];
        }
        if (child && !details[parent].includes(child)) {
            details[parent].push(child);
        }
    }

    return { options, details };
}

const CrudPanel: React.FC<{ onDataChanged?: () => void }> = ({ onDataChanged }) => {
    const [operation, setOperation] = useState<Operation>('read');

    // Dynamic Metadata State
    const [sessionIds, setSessionIds] = useState<string[]>([]);
    const [sessionId, setSessionId] = useState('');
    const[sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
    const [logicalFields, setLogicalFields] = useState<string[]>([]);

    const [selectFields, setSelectFields] = useState<string[]>([]);
    const [filters, setFilters] = useState<FilterInput[]>([{ field: '', op: 'eq', value: '' }]);
    const[limit, setLimit] = useState<number | string>(10);
    const[payloadJson, setPayloadJson] = useState(DEFAULT_PAYLOAD);
    const [showEntityInspector, setShowEntityInspector] = useState(false);
    const [expandedEntities, setExpandedEntities] = useState<Record<string, boolean>>({});

    // Key-Value builder state for Updates (No more JSON!)
    const [updateKVs, setUpdateKVs] = useState<{field: string, value: string}[]>([{field: '', value: ''}]);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [resultTabs, setResultTabs] = useState<ResultTab[]>([]);
    const [activeTabId, setActiveTabId] = useState<number | null>(null);
    const groupedSelect = buildGroupedSelectOptions(logicalFields);
    const inspectorTree = useMemo(() => buildInspectorTree(logicalFields), [logicalFields]);

    const loadSessions = useCallback(async () => {
        try {
            const ids = await fetchSessions();
            setSessionIds(ids);
            setSessionId((current) => {
                if (current && ids.includes(current)) {
                    return current;
                }
                return ids[0] ?? '';
            });
        } catch (err) {
            console.error('Session load error:', err);
        }
    }, []);

    // Initial Load
    useEffect(() => {
        void loadSessions();
    }, [loadSessions]);

    useEffect(() => {
        const intervalId = window.setInterval(() => {
            void loadSessions();
        }, 4000);
        return () => {
            window.clearInterval(intervalId);
        };
    }, [loadSessions]);

    // Load Metadata when Session changes
    useEffect(() => {
        if (!sessionId) return;
        fetchLogicalFields(sessionId).then(setLogicalFields).catch(err => console.error("Field load error:", err));
        fetchSessionInfo(sessionId).then(setSessionInfo).catch(() => setSessionInfo(null));
    },[sessionId]);

    const handleUpdateChange = (index: number, key: 'field'|'value', val: string) => {
        setUpdateKVs(prev => {
            const newKVs = [...prev];
            newKVs[index] = { ...newKVs[index], [key]: val };
            return newKVs;
        });
    };

    const handleFilterChange = (index: number, key: keyof FilterInput, val: string) => {
        setFilters(prev => {
            const next = [...prev];
            next[index] = { ...next[index], [key]: val };
            return next;
        });
    };

    const executeOp = useCallback(async () => {
        setError(null);
        setLoading(true);

        const req: QueryRequest = { operation, table: 'chiral_data', session_id: sessionId };

        if (operation === 'read') {
            if (selectFields.length === 0) {
                setError('Please select at least one field to read.');
                setLoading(false); return;
            }
            req.select = selectFields;
            if (limit) req.limit = typeof limit === 'string' ? parseInt(limit, 10) : limit;
        }

        const builtFilters = filters
            .filter((f) => f.field.trim() !== '' && f.value.trim() !== '')
            .map((f) => {
                let val: string | number | boolean = f.value;
                if (!isNaN(Number(val)) && val.trim() !== '') val = Number(val);
                else if (val.toLowerCase() === 'true') val = true;
                else if (val.toLowerCase() === 'false') val = false;
                return { field: f.field, op: f.op, value: val };
            });

        if (builtFilters.length > 0) {
            req.filters = builtFilters;
        }

        if (operation === 'create') {
            try {
                const parsedPayload = JSON.parse(payloadJson) as Record<string, unknown>;
                const payloadSessionId = parsedPayload.session_id;
                const missingPayloadSessionId =
                    payloadSessionId === undefined ||
                    payloadSessionId === null ||
                    (typeof payloadSessionId === 'string' && payloadSessionId.trim() === '');

                // Keep create behavior aligned with selected session context.
                if (missingPayloadSessionId && sessionId.trim() !== '') {
                    parsedPayload.session_id = sessionId;
                }

                req.payload = parsedPayload;
            }
            catch { setError('Invalid JSON payload for CREATE'); setLoading(false); return; }
        }

        if (operation === 'update') {
            const updates: Record<string, string | number | boolean> = {};
            updateKVs.forEach(kv => {
                if (kv.field && kv.value) {
                    let val: string | number | boolean = kv.value;
                    if (!isNaN(Number(val)) && val.trim() !== '') val = Number(val);
                    else if (val.toLowerCase() === 'true') val = true;
                    else if (val.toLowerCase() === 'false') val = false;
                    updates[kv.field] = val;
                }
            });
            if (Object.keys(updates).length === 0) {
                setError('Please provide at least one update field and value.');
                setLoading(false); return;
            }
            req.updates = updates;
        }

        try {
            const response = await executeQuery(req);
            const tabLabel = `${operation.toUpperCase()} LOGICAL`;
            const newTab: ResultTab = { id: ++tabCounter, label: tabLabel, response, request: req, timestamp: new Date() };
            setResultTabs(prev => [...prev, newTab]);
            setActiveTabId(newTab.id);
            void loadSessions();

            // Refresh metadata to reflect new rows
            fetchSessionInfo(sessionId).then(setSessionInfo);

            if (operation !== 'read' && onDataChanged) {
                onDataChanged();
                fetchLogicalFields(sessionId).then(setLogicalFields);
            }
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    },[operation, sessionId, selectFields, filters, payloadJson, updateKVs, limit, onDataChanged, loadSessions]);

    const activeTab = resultTabs.find(t => t.id === activeTabId);

    const toggleEntity = (path: string) => {
        setExpandedEntities((prev) => ({ ...prev, [path]: !prev[path] }));
    };

    const renderInspectorNode = (node: InspectorNode, depth = 0): React.ReactNode => {
        const hasChildren = node.children.length > 0;
        const isExpanded = !!expandedEntities[node.path];

        return (
            <div key={node.path}>
                <button
                    type="button"
                    className={`crud-entity-node ${hasChildren ? 'crud-entity-node-parent' : 'crud-entity-node-leaf'}`}
                    style={{ paddingLeft: `${8 + depth * 14}px` }}
                    onClick={() => {
                        if (hasChildren) {
                            toggleEntity(node.path);
                        }
                    }}
                >
                    <span className="crud-entity-node-marker" aria-hidden="true">
                        {hasChildren ? (isExpanded ? '-' : '+') : '.'}
                    </span>
                    <span className="crud-entity-node-label">{node.name}</span>
                </button>
                {hasChildren && isExpanded && (
                    <div className="crud-entity-children">
                        {node.children.map((child) => renderInspectorNode(child, depth + 1))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="crud-panel">
            <div className="crud-form-container" style={{ width: 400 }}>
                <div className="crud-form">
                    <h2 className="crud-title">Logical Operations</h2>

                    <div className="crud-row">
                        <div className="crud-op-selector">
                            {(['read', 'create', 'update', 'delete'] as Operation[]).map(op => (
                                <button key={op} className={`crud-op-btn ${operation === op ? 'active' : ''} crud-op-${op}`} onClick={() => setOperation(op)}>
                                    {op.toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="crud-row">
                        <label>Session Context</label>
                        <SearchableDropdown options={sessionIds} value={sessionId} onChange={(v) => setSessionId(v as string)} placeholder="Select session..." allowFreeText />

                        {/* Dynamic Session Status Widget */}
                        {sessionInfo && (
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px', padding: '6px 10px', background: 'var(--bg-muted)', borderRadius: '6px', display: 'flex', gap: '14px', border: '1px solid var(--border)' }}>
                                <span>Status: <b style={{color: 'var(--accent)'}}>{String(sessionInfo.status).toUpperCase()}</b></span>
                                <span>Records: <b style={{color: 'var(--text-primary)'}}>{sessionInfo.record_count}</b></span>
                                <span>Schema: <b style={{color: 'var(--text-primary)'}}>v{sessionInfo.schema_version}</b></span>
                            </div>
                        )}
                    </div>

                    <div className="crud-row">
                        <button
                            type="button"
                            className="crud-entity-toggle"
                            onClick={() => setShowEntityInspector((prev) => !prev)}
                        >
                            {showEntityInspector ? 'Hide Entity Inspector' : 'Open Entity Inspector'}
                        </button>
                        {showEntityInspector && (
                            <div className="crud-entity-panel" role="tree" aria-label="Entity attributes">
                                {inspectorTree.length === 0 ? (
                                    <div className="crud-entity-empty">No entity attributes available for this session.</div>
                                ) : (
                                    inspectorTree.map((node) => renderInspectorNode(node))
                                )}
                            </div>
                        )}
                    </div>

                    {operation === 'read' && (
                        <>
                            <div className="crud-row">
                                <label>Select Fields</label>
                                <SearchableDropdown
                                    options={groupedSelect.options}
                                    optionDetails={groupedSelect.details}
                                    value={selectFields}
                                    onChange={(v) => setSelectFields(v as string[])}
                                    placeholder="Select fields..."
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
                        <label>Target Filters</label>
                        {filters.map((filter, i) => (
                            <div key={i} className="crud-filter-row" style={{marginBottom: '6px'}}>
                                <SearchableDropdown options={logicalFields} value={filter.field} onChange={(v) => handleFilterChange(i, 'field', v as string)} placeholder="Field..." allowFreeText />
                                <select value={filter.op} onChange={e => handleFilterChange(i, 'op', e.target.value)} className="crud-select crud-select-sm">
                                    <option value="eq">=</option>
                                    <option value="neq">≠</option>
                                    <option value="gt">&gt;</option>
                                    <option value="gte">≥</option>
                                    <option value="lt">&lt;</option>
                                    <option value="lte">≤</option>
                                </select>
                                <input className="crud-input crud-input-sm" value={filter.value} onChange={e => handleFilterChange(i, 'value', e.target.value)} placeholder="Value..." />
                                {filters.length > 1 && (
                                    <button style={{background:'transparent', border:'none', color:'var(--danger-color)', cursor:'pointer', padding:'0 4px', fontSize: '16px', fontWeight: 'bold'}} onClick={() => setFilters(filters.filter((_, idx) => idx !== i))}>×</button>
                                )}
                            </div>
                        ))}
                        <button onClick={() => setFilters([...filters, { field: '', op: 'eq', value: '' }])} style={{alignSelf: 'flex-start', background: 'var(--bg-muted)', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '11px', padding: '4px 8px', cursor: 'pointer', color: 'var(--text-secondary)'}}>+ Add Filter</button>
                    </div>

                    {operation === 'create' && (
                        <div className="crud-row">
                            <label>Payload (JSON)</label>
                            <textarea className="crud-textarea" style={{minHeight: '150px'}} value={payloadJson} onChange={e => setPayloadJson(e.target.value)} />
                        </div>
                    )}

                    {operation === 'update' && (
                        <div className="crud-row">
                            <label>Logical Updates</label>
                            {updateKVs.map((kv, i) => (
                                <div key={i} className="crud-filter-row" style={{marginBottom: '6px'}}>
                                    <SearchableDropdown options={logicalFields} value={kv.field} onChange={(v) => handleUpdateChange(i, 'field', v as string)} placeholder="Field" allowFreeText />
                                    <input className="crud-input crud-input-sm" value={kv.value} onChange={(e) => handleUpdateChange(i, 'value', e.target.value)} placeholder="New Value" />
                                    {updateKVs.length > 1 && (
                                        <button style={{background:'transparent', border:'none', color:'var(--danger-color)', cursor:'pointer', padding:'0 4px', fontSize: '16px', fontWeight: 'bold'}} onClick={() => setUpdateKVs(updateKVs.filter((_, idx) => idx !== i))}>×</button>
                                    )}
                                </div>
                            ))}
                            <button onClick={() => setUpdateKVs([...updateKVs, {field: '', value: ''}])} style={{alignSelf: 'flex-start', background: 'var(--bg-muted)', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '11px', padding: '4px 8px', cursor: 'pointer', color: 'var(--text-secondary)'}}>+ Add Field</button>
                        </div>
                    )}

                    <button className="crud-submit-btn" onClick={() => { executeOp(); }} disabled={loading} style={{marginTop: 'auto'}}>
                        {loading ? 'Executing...' : `Execute ${operation.toUpperCase()}`}
                    </button>
                </div>
            </div>

            <div className="crud-results">
                {error && (
                    <div className="crud-error-banner" style={{margin: '16px'}}>
                        {error} <button className="crud-error-dismiss" onClick={() => setError(null)}>✕</button>
                    </div>
                )}
                <div className="crud-tabs-header">
                    {resultTabs.map(tab => (
                        <div key={tab.id} className={`crud-tab ${activeTabId === tab.id ? 'active' : ''}`} onClick={() => setActiveTabId(tab.id)}>
                            {tab.label}
                            <span className="crud-tab-close" onClick={(e) => { e.stopPropagation(); setResultTabs(prev => prev.filter(t => t.id !== tab.id)); }}>✕</span>
                        </div>
                    ))}
                </div>

                {activeTab ? (
                    <div className="crud-tab-content crud-result-view">
                        <div className="crud-result-meta">
                            <span className="crud-result-time">⏱ {activeTab.timestamp.toLocaleTimeString()}</span>
                            {activeTab.response.row_count !== undefined && <span className="crud-result-badge crud-result-count">{activeTab.response.row_count} rows read</span>}
                            {activeTab.response.affected_rows !== undefined && <span className="crud-result-badge">{activeTab.response.affected_rows} rows written</span>}
                        </div>

                        {activeTab.response.rows && activeTab.response.rows.length > 0 && (
                            <div className="crud-data-scroll">
                                <table className="crud-data-table">
                                    <thead><tr>{Object.keys(activeTab.response.rows[0]).map(k => <th key={k}>{k}</th>)}</tr></thead>
                                    <tbody>
                                        {activeTab.response.rows.map((row: Record<string, unknown>, i: number) => (
                                            <tr key={i}>
                                                {Object.keys(activeTab.response.rows![0]).map(k => (
                                                    <td key={k}>{typeof row[k] === 'object' ? <JsonCell data={row[k]} /> : String(row[k])}</td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {/* Hidden Physical Debug Info */}
                        <details style={{marginTop: '20px', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '12px'}}>
                            <summary>View SQL Execution Details</summary>
                            <div className="crud-sql-block" style={{ marginTop: '12px', padding: '12px' }}>
                                <pre>{activeTab.response.sql}</pre>
                                <hr style={{margin: '10px 0', border: 'none', borderTop: '1px solid var(--border)'}}/>
                                <pre>{JSON.stringify(activeTab.response.params, null, 2)}</pre>
                            </div>
                        </details>
                    </div>
                ) : (
                    <div className="crud-tab-content-empty">Execute an operation to see results.</div>
                )}
            </div>
        </div>
    );
};
export default CrudPanel;
