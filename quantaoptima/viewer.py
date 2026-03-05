"""
Audit Chain Viewer — renders an AuditChain export as an interactive HTML timeline.

Generates a self-contained HTML file that anyone can open in a browser to
inspect the decision chain: what happened, when, by whom, with what inputs
and outputs, and whether the chain is cryptographically intact.

Usage (from Python):
    from quantaoptima.audit import AuditChain
    from quantaoptima.viewer import render_chain_html

    chain = AuditChain(scope="my-workflow")
    chain.log("query", {"q": "revenue?"}, {"answer": "$4.2M"})
    chain.log("decision", {"options": ["A", "B"]}, {"chosen": "A"})

    render_chain_html(chain, "audit_viewer.html")

Usage (from CLI):
    python -m quantaoptima.viewer audit_export.json --output viewer.html

Usage (from MCP):
    The quantaoptima_export_chain tool can generate this automatically
    when the user asks for a visual export.
"""

import json
import time
import html as html_module
from typing import Optional, Dict, Any, Union
from pathlib import Path


def render_chain_html(
    chain_or_data: Any,
    output_path: str,
    title: str = "Audit Chain Viewer",
) -> str:
    """
    Render an audit chain as an interactive HTML file.

    Args:
        chain_or_data: An AuditChain instance, or a dict from chain.export_dict(),
                      or a path to a JSON export file.
        output_path: Where to save the HTML file.
        title: Page title.

    Returns:
        The output file path.
    """
    # Normalize input to a dict
    if isinstance(chain_or_data, (str, Path)):
        with open(chain_or_data) as f:
            data = json.load(f)
    elif hasattr(chain_or_data, 'export_dict'):
        data = chain_or_data.export_dict()
    else:
        data = chain_or_data

    blocks = data.get("blocks", [])
    scope = data.get("scope", "unknown")
    chain_length = data.get("chain_length", len(blocks))
    verified = data.get("verified", False)
    exported_at = data.get("exported_at", time.time())

    # Build action type stats
    action_counts: Dict[str, int] = {}
    actors: set = set()
    for b in blocks:
        at = b.get("action_type", "unknown")
        action_counts[at] = action_counts.get(at, 0) + 1
        actors.add(b.get("actor", "unknown"))

    # Time range
    if blocks:
        t_start = blocks[0].get("timestamp", 0)
        t_end = blocks[-1].get("timestamp", 0)
        duration = t_end - t_start
    else:
        t_start = t_end = duration = 0

    # Generate HTML for each block
    block_html_parts = []
    for b in blocks:
        block_num = b.get("block_number", "?")
        action = html_module.escape(str(b.get("action_type", "unknown")))
        actor = html_module.escape(str(b.get("actor", "unknown")))
        ts = b.get("timestamp", 0)
        sig = b.get("signature", "")[:16] + "..."
        prev_hash = b.get("previous_hash", "")[:16] + "..."

        before_json = html_module.escape(json.dumps(b.get("state_before", {}), indent=2, default=str))
        after_json = html_module.escape(json.dumps(b.get("state_after", {}), indent=2, default=str))
        meta_json = html_module.escape(json.dumps(b.get("metadata", {}), indent=2, default=str))

        # Color based on action type
        colors = {
            "query": "#818cf8",
            "decision": "#fb923c",
            "api_call": "#34d399",
            "calculation": "#f472b6",
            "transform": "#a78bfa",
            "optimization_start": "#6366f1",
            "optimization_complete": "#22d3ee",
            "optimization_step": "#94a3b8",
            "benchmark": "#fbbf24",
            "file_write": "#34d399",
            "approval": "#22c55e",
            "error": "#ef4444",
        }
        color = colors.get(action, "#6366f1")

        time_str = _format_timestamp(ts)

        block_html_parts.append(f"""
        <div class="block" onclick="toggleBlock(this)">
            <div class="block-header">
                <div class="block-num">#{block_num}</div>
                <div class="block-action" style="color:{color};">{action}</div>
                <div class="block-actor">{actor}</div>
                <div class="block-time">{time_str}</div>
                <div class="block-sig" title="Signature: {sig}">🔏 {sig}</div>
            </div>
            <div class="block-detail" style="display:none;">
                <div class="detail-row">
                    <div class="detail-label">Chain Link</div>
                    <div class="detail-value mono">prev: {prev_hash}</div>
                </div>
                <div class="detail-columns">
                    <div class="detail-col">
                        <div class="detail-label">State Before (Input)</div>
                        <pre>{before_json}</pre>
                    </div>
                    <div class="detail-col">
                        <div class="detail-label">State After (Output)</div>
                        <pre>{after_json}</pre>
                    </div>
                </div>
                <div class="detail-row" style="margin-top:8px;">
                    <div class="detail-label">Metadata</div>
                    <pre>{meta_json}</pre>
                </div>
            </div>
        </div>
        """)

    blocks_html = "\n".join(block_html_parts)

    # Action type badges
    action_badges = " ".join(
        f'<span class="badge">{html_module.escape(k)}: {v}</span>'
        for k, v in sorted(action_counts.items(), key=lambda x: -x[1])
    )

    verified_class = "verified" if verified else "tampered"
    verified_text = "VERIFIED ✓" if verified else "TAMPERED ✗"

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_module.escape(title)}</title>
<style>
:root {{
  --bg: #0a0a0f;
  --surface: #12121a;
  --border: #1e1e2e;
  --text: #e4e4ef;
  --muted: #8888a0;
  --accent: #6366f1;
  --green: #34d399;
  --red: #ef4444;
  --orange: #fb923c;
  --mono: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
  --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: var(--sans); background: var(--bg); color: var(--text); line-height: 1.6; padding: 24px; }}
.container {{ max-width: 1000px; margin: 0 auto; }}

/* Header */
.header {{ text-align: center; padding: 32px 0; }}
.header h1 {{ font-size: 2rem; font-weight: 700; margin-bottom: 8px; }}
.header .scope {{ color: var(--muted); font-size: 1.1rem; }}

/* Summary cards */
.summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; text-align: center; }}
.card .value {{ font-size: 1.5rem; font-weight: 700; color: var(--accent); }}
.card .label {{ font-size: 0.8rem; color: var(--muted); }}
.card.verified .value {{ color: var(--green); }}
.card.tampered .value {{ color: var(--red); }}

/* Action badges */
.badges {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; justify-content: center; }}
.badge {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 4px 12px; font-size: 0.8rem; color: var(--muted); }}

/* Filter */
.filter-bar {{ display: flex; gap: 8px; margin: 24px 0 16px; align-items: center; }}
.filter-bar input {{ background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; color: var(--text); font-size: 0.9rem; flex: 1; }}
.filter-bar input::placeholder {{ color: var(--muted); }}

/* Timeline */
.timeline {{ position: relative; padding-left: 32px; }}
.timeline::before {{ content: ''; position: absolute; left: 12px; top: 0; bottom: 0; width: 2px; background: var(--border); }}

.block {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; cursor: pointer; transition: border-color 0.2s; position: relative; }}
.block:hover {{ border-color: var(--accent); }}
.block::before {{ content: ''; position: absolute; left: -26px; top: 16px; width: 10px; height: 10px; border-radius: 50%; background: var(--accent); border: 2px solid var(--bg); }}

.block-header {{ display: grid; grid-template-columns: 48px 140px 120px 1fr auto; align-items: center; padding: 12px 16px; gap: 12px; }}
.block-num {{ font-family: var(--mono); font-size: 0.85rem; color: var(--muted); }}
.block-action {{ font-weight: 600; font-size: 0.9rem; }}
.block-actor {{ font-size: 0.85rem; color: var(--muted); }}
.block-time {{ font-size: 0.8rem; color: var(--muted); text-align: right; }}
.block-sig {{ font-family: var(--mono); font-size: 0.75rem; color: var(--muted); }}

.block-detail {{ padding: 0 16px 16px; border-top: 1px solid var(--border); }}
.detail-row {{ margin-top: 12px; }}
.detail-label {{ font-size: 0.75rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }}
.detail-value {{ font-size: 0.85rem; }}
.detail-columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }}
.detail-col {{ min-width: 0; }}
pre {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; font-family: var(--mono); font-size: 0.8rem; overflow-x: auto; white-space: pre-wrap; word-break: break-word; color: var(--muted); line-height: 1.5; }}
.mono {{ font-family: var(--mono); font-size: 0.8rem; }}

/* Footer */
.footer {{ text-align: center; padding: 32px 0; color: var(--muted); font-size: 0.8rem; }}

@media (max-width: 768px) {{
  .summary {{ grid-template-columns: repeat(2, 1fr); }}
  .block-header {{ grid-template-columns: 40px 1fr; }}
  .block-actor, .block-time, .block-sig {{ display: none; }}
  .detail-columns {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<div class="container">

<div class="header">
  <h1>🔏 {html_module.escape(title)}</h1>
  <div class="scope">Scope: <strong>{html_module.escape(scope)}</strong></div>
</div>

<div class="summary">
  <div class="card {verified_class}">
    <div class="value">{verified_text}</div>
    <div class="label">Chain Integrity</div>
  </div>
  <div class="card">
    <div class="value">{chain_length}</div>
    <div class="label">Total Actions</div>
  </div>
  <div class="card">
    <div class="value">{len(actors)}</div>
    <div class="label">Actors</div>
  </div>
  <div class="card">
    <div class="value">{_format_duration(duration)}</div>
    <div class="label">Duration</div>
  </div>
</div>

<div class="badges">
  {action_badges}
</div>

<div class="filter-bar">
  <input type="text" id="filter" placeholder="Filter by action type, actor, or content..." oninput="filterBlocks(this.value)">
</div>

<div class="timeline" id="timeline">
{blocks_html}
</div>

<div class="footer">
  <p>Generated by QuantaOptima Audit Chain Viewer | Scope: {html_module.escape(scope)} | {chain_length} blocks | HMAC-SHA256</p>
  <p>Exported: {_format_timestamp(exported_at)}</p>
</div>

</div>

<script>
function toggleBlock(el) {{
  const detail = el.querySelector('.block-detail');
  if (detail) {{
    detail.style.display = detail.style.display === 'none' ? 'block' : 'none';
  }}
}}

function filterBlocks(query) {{
  const blocks = document.querySelectorAll('.block');
  const q = query.toLowerCase();
  blocks.forEach(b => {{
    const text = b.textContent.toLowerCase();
    b.style.display = text.includes(q) ? '' : 'none';
  }});
}}
</script>

</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(full_html)

    return output_path


def _format_timestamp(ts: float) -> str:
    """Format a Unix timestamp as human-readable."""
    try:
        import datetime
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return str(ts)


def _format_duration(seconds: float) -> str:
    """Format a duration in seconds as human-readable."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


# ============================================================
# CLI entry point
# ============================================================

def main():
    """CLI: python -m quantaoptima.viewer <input.json> [--output viewer.html] [--title 'My Audit']"""
    import argparse
    parser = argparse.ArgumentParser(description="Render an audit chain export as an interactive HTML viewer.")
    parser.add_argument("input", help="Path to audit chain JSON export")
    parser.add_argument("--output", "-o", default="audit_viewer.html", help="Output HTML file path")
    parser.add_argument("--title", "-t", default="Audit Chain Viewer", help="Page title")
    args = parser.parse_args()

    output = render_chain_html(args.input, args.output, args.title)
    print(f"Viewer generated: {output}")


if __name__ == "__main__":
    main()
