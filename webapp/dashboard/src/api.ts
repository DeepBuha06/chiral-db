/* ─── API utility for communicating with the ChiralDB backend ─── */

const API_BASE = 'http://127.0.0.1:8000';

export interface QueryRequest {
    operation: 'read' | 'create' | 'update' | 'delete';
    table?: string;
    session_id?: string;
    select?: string[];
    filters?: { field: string; operator: string; value: unknown }[];
    payload?: Record<string, unknown>;
    updates?: Record<string, unknown>;
    limit?: number;
    offset?: number;
}

export interface QueryResponse {
    sql?: string;
    params?: Record<string, unknown>;
    rows?: Record<string, unknown>[];
    row_count?: number;
    affected_rows?: number;
    mode?: string;
    error?: string;
}

export async function executeQuery(request: QueryRequest): Promise<QueryResponse> {
    const res = await fetch(`${API_BASE}/query/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
    });

    if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail));
    }

    return res.json();
}

export async function checkHealth(): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE}/`);
        return res.ok;
    } catch {
        return false;
    }
}

export interface SchemaColumn {
    name: string;
    type: string;
}

export interface SchemaForeignKey {
    constrained_columns: string[];
    referred_table: string;
    referred_columns: string[];
}

export interface TableSchema {
    columns: SchemaColumn[];
    primary_keys: string[];
    foreign_keys: SchemaForeignKey[];
    sampleData?: Record<string, string>[];
}

export type DatabaseSchema = Record<string, TableSchema>;

export async function fetchSchema(): Promise<DatabaseSchema> {
    const res = await fetch(`${API_BASE}/schema/metadata`, { method: 'GET' });
    if (!res.ok) throw new Error('Failed to fetch schema');
    return res.json();
}

export async function flushSession(sessionId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/flush/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    });

    if (!res.ok) {
        const errBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail));
    }

    return res.json();
}
