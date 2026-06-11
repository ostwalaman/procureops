import type { AuditEvent, ExceptionDetail } from "../types";

const titleCase = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function AgentPanel({
  detail,
  audit,
  busy,
  onDecision,
  onRetriage,
}: {
  detail: ExceptionDetail;
  audit: AuditEvent[];
  busy: boolean;
  onDecision: (decision: string) => void;
  onRetriage: () => void;
}) {
  const confidence = Math.round(Number(detail.confidence) * 100);
  return (
    <aside className="agent-panel">
      <div className="section-heading">
        <div><h2>Agent Recommendation</h2><span>Governed decision support</span></div>
        <button className="text-button" onClick={onRetriage} disabled={busy}>Re-run</button>
      </div>
      <div className="confidence">
        <div><span>Confidence score</span><strong>{confidence}%</strong></div>
        <div className="confidence-track"><span style={{ width: `${confidence}%` }} /></div>
        <small>Below 75% automatically routes to manual review.</small>
      </div>
      <div className="recommendation">
        <span>Recommended action</span>
        <h3>{detail.recommendation}</h3>
        <div className="note"><strong>Escalation note</strong><p>{detail.escalation_note}</p></div>
      </div>
      <div className="actions">
        <button className="primary" disabled={busy} onClick={() => onDecision("approve_recommendation")}>Approve recommendation</button>
        <button disabled={busy} onClick={() => onDecision("send_to_manual_review")}>Send to manual review</button>
      </div>
      <section className="audit">
        <div className="section-heading"><div><h3>Audit &amp; agent trace</h3><span>{audit.length} immutable events</span></div></div>
        <div className="timeline">
          {audit.map((event) => (
            <div className="event" key={event.id}>
              <span className="event-dot" />
              <div><strong>{titleCase(event.event_type)}</strong><small>{event.actor} · {new Date(event.created_at).toLocaleString()}</small></div>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}
