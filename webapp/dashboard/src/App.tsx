import { useState, useCallback, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type NodeTypes,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import DatabaseNode from './DatabaseNode';
import CrudPanel from './CrudPanel';
import { fetchSchema, type DatabaseSchema } from './api';
import { type Node, type Edge, MarkerType } from '@xyflow/react';

/* Register our custom node type */
const nodeTypes: NodeTypes = {
  databaseTable: DatabaseNode,
};

type View = 'schema' | 'crud';

/* ─── Icon components for sidebar ─── */
const SchemaIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="3" y1="9" x2="21" y2="9" />
    <line x1="9" y1="21" x2="9" y2="9" />
  </svg>
);

const CrudIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="12" y1="18" x2="12" y2="12" />
    <line x1="9" y1="15" x2="15" y2="15" />
  </svg>
);

export default function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [view, setView] = useState<View>('schema');
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [allTableNames, setAllTableNames] = useState<string[]>([]);

  const [schemaLoading, setSchemaLoading] = useState(true);

  const loadSchema = useCallback(async () => {
    try {
      setSchemaLoading(true);
      const schemaObj = await fetchSchema();

      const newNodes: Node[] = [];
      const newEdges: Edge[] = [];

      const tables = Object.keys(schemaObj);
      setAllTableNames(tables);

      let target = selectedTable;
      if (!target || !tables.includes(target)) {
        target = tables.includes('chiral_data') ? 'chiral_data' : tables[0];
        if (!target) return;
      }

      const targetData = schemaObj[target];
      if (!targetData) return;

      // Heuristic relation discovery!
      const isRelColumn = (colName: string, tableName: string) => colName === `${tableName}_id` || (tableName === 'session_metadata' && colName === 'session_id');

      // Children: tables that have a foreign key pointing to target
      const children = tables.filter(t => t !== target && schemaObj[t].columns.some(c => isRelColumn(c.name, target)));

      // Parents: target has a foreign key pointing to these tables
      const parents = tables.filter(t => t !== target && targetData.columns.some(c => isRelColumn(c.name, t)));

      // 1. Render Target Node in Center
      newNodes.push({
        id: target,
        type: 'databaseTable',
        position: { x: 400, y: 320 },
        data: {
          label: target,
          isStaging: target.includes('staging'),
          sampleData: targetData.sampleData || [],
          columns: targetData.columns.map(c => ({
            name: c.name, type: c.type, isPrimaryKey: targetData.primary_keys.includes(c.name), isForeignKey: c.name.includes('_id')
          }))
        }
      });

      // 2. Render Parents Above
      parents.forEach((p, i) => {
        const pData = schemaObj[p];
        newNodes.push({
          id: p,
          type: 'databaseTable',
          position: { x: 400 + (i - Math.floor(parents.length / 2)) * 400, y: 0 },
          data: {
            label: p, isStaging: p.includes('staging'), sampleData: pData.sampleData || [],
            columns: pData.columns.map(c => ({ name: c.name, type: c.type, isPrimaryKey: pData.primary_keys.includes(c.name), isForeignKey: c.name.includes('_id') }))
          }
        });
        newEdges.push({
          id: `e-${p}-${target}`, source: p, target: target, animated: true,
          style: { stroke: '#6366f1', strokeWidth: 2, strokeDasharray: '5 5' },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1', width: 20, height: 20 }
        });
      });

      // 3. Render Children Below
      children.forEach((c, i) => {
        const cData = schemaObj[c];
        newNodes.push({
          id: c,
          type: 'databaseTable',
          position: { x: 400 + (i - Math.floor(children.length / 2)) * 400, y: 640 },
          data: {
            label: c, isStaging: c.includes('staging'), sampleData: cData.sampleData || [],
            columns: cData.columns.map(col => ({ name: col.name, type: col.type, isPrimaryKey: cData.primary_keys.includes(col.name), isForeignKey: col.name.includes('_id') }))
          }
        });

        // Dynamic children get distinctly bright dashed orange bounds
        const isDynamicChild = c.startsWith('chiral_data_') && c !== 'chiral_data_comments' && c !== 'chiral_data_events';
        newEdges.push({
          id: `e-${target}-${c}`, source: target, target: c, animated: true,
          style: { stroke: isDynamicChild ? '#fb923c' : '#6366f1', strokeWidth: isDynamicChild ? 2.5 : 2, strokeDasharray: '5 5' },
          markerEnd: { type: MarkerType.ArrowClosed, color: isDynamicChild ? '#fb923c' : '#6366f1', width: 20, height: 20 }
        });
      });

      setNodes(newNodes);
      setEdges(newEdges);
    } catch (err) {
      console.error("Failed to load schema", err);
    } finally {
      setSchemaLoading(false);
    }
  }, [setNodes, setEdges, selectedTable]); // Auto-recompile layout when dropdown changes

  useEffect(() => {
    loadSchema();
  }, [loadSchema, refreshKey]);

  const onInit = useCallback(() => {
    console.log('[ChiralDB] Dashboard initialised');
  }, []);

  const handleDataChanged = useCallback(() => {
    setRefreshKey(prev => prev + 1);
  }, []);

  return (
    <div className="app-shell">
      {/* ── Sidebar ── */}
      <nav className="app-sidebar">
        <div className="sidebar-brand">
          <span className="app-logo">◈</span>
        </div>
        <div className="sidebar-nav">
          <button
            className={`sidebar-btn ${view === 'schema' ? 'active' : ''}`}
            onClick={() => setView('schema')}
            title="Schema View"
          >
            <SchemaIcon />
            <span className="sidebar-label">Schema</span>
          </button>
          <button
            className={`sidebar-btn ${view === 'crud' ? 'active' : ''}`}
            onClick={() => setView('crud')}
            title="CRUD Operations"
          >
            <CrudIcon />
            <span className="sidebar-label">CRUD</span>
          </button>
        </div>
      </nav>

      {/* ── Main content area ── */}
      <div className="app-main">
        {/* ── Top bar ── */}
        <header className="app-header">
          <div className="app-brand">
            <h1>Chiral<span className="brand-accent">DB</span></h1>
          </div>
          <p className="app-subtitle">
            {view === 'schema' ? 'Logical Schema Dashboard' : 'Query Executor & CRUD Operations'}
          </p>
          <div className="header-status">
            {view === 'schema' && allTableNames.length > 0 && (
              <div className="schema-dropdown-container">
                <span className="schema-dropdown-label">Explore Table:</span>
                <select
                  className="schema-dropdown"
                  value={selectedTable || (allTableNames.includes('chiral_data') ? 'chiral_data' : allTableNames[0])}
                  onChange={(e) => setSelectedTable(e.target.value)}
                >
                  {allTableNames.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className={`status-dot ${refreshKey > 0 ? 'status-dot--active' : ''}`} />
              <span className="status-text">Live</span>
            </div>
          </div>
        </header>

        {/* ── Schema view ── */}
        {view === 'schema' && (
          <>
            <div className="flow-container" key={`flow-${refreshKey}`}>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onInit={onInit}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.25 }}
                minZoom={0.2}
                maxZoom={2}
                proOptions={{ hideAttribution: true }}
              >
                <Background variant={BackgroundVariant.Dots} gap={24} size={2} color="#000000" style={{ opacity: 0.3 }} />
                <Controls position="bottom-right" showInteractive={false} />
                <MiniMap
                  nodeColor={() => '#3b82f6'}
                  maskColor="rgba(248,249,251,0.7)"
                  style={{ background: '#f3f4f6', borderRadius: 8 }}
                />
              </ReactFlow>
            </div>

            {/* ── Legend ── */}
            <footer className="app-legend">
              <span className="legend-item"><span className="legend-dot pk-dot" /> Primary Key</span>
              <span className="legend-item"><span className="legend-dot fk-dot" /> Foreign Key</span>
              <span className="legend-item"><span className="legend-dot arrow-dot" /> → Directed Relationship</span>
            </footer>
          </>
        )}

        {/* ── CRUD view ── */}
        {view === 'crud' && (
          <CrudPanel onDataChanged={handleDataChanged} />
        )}
      </div>
    </div>
  );
}
