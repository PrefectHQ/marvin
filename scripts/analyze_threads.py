#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx", "pydantic-settings", "plotly", "pandas"]
# ///
"""
Analyze Slack thread data from Turso and generate an HTML report.

Usage:
    ./scripts/analyze_threads.py              # generates report.html
    ./scripts/analyze_threads.py --open       # generates and opens in browser
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime

import httpx
import plotly.graph_objects as go
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"), extra="ignore"
    )
    turso_url: str
    turso_token: str

    @property
    def turso_host(self) -> str:
        url = self.turso_url
        if url.startswith("libsql://"):
            url = url[len("libsql://") :]
        return url


def turso_query(settings: Settings, sql: str) -> list[dict]:
    """Query Turso."""
    response = httpx.post(
        f"https://{settings.turso_host}/v2/pipeline",
        headers={
            "Authorization": f"Bearer {settings.turso_token}",
            "Content-Type": "application/json",
        },
        json={
            "requests": [
                {"type": "execute", "stmt": {"sql": sql}},
                {"type": "close"},
            ]
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    result = data["results"][0]
    if result["type"] == "error":
        raise Exception(f"Turso error: {result['error']}")

    cols = [c["name"] for c in result["response"]["result"]["cols"]]
    rows = result["response"]["result"]["rows"]

    def extract(cell):
        if cell is None:
            return None
        if isinstance(cell, dict):
            return cell.get("value")
        return cell

    return [dict(zip(cols, [extract(c) for c in row])) for row in rows]


def generate_report(settings: Settings) -> str:
    """Generate HTML report from Turso data."""
    print("fetching data from Turso...", flush=True)

    rows = turso_query(settings, "SELECT key, name, last_seen, metadata FROM assets")
    print(f"  fetched {len(rows)} threads", flush=True)

    # Parse metadata
    threads = []
    for row in rows:
        meta = {}
        if row.get("metadata"):
            try:
                meta = json.loads(row["metadata"])
            except Exception:
                pass  # malformed metadata, treat as empty

        # Only include if has actual data
        msg_count = meta.get("message_count")
        if msg_count is not None and meta.get("title"):
            threads.append(
                {
                    "key": row["key"],
                    "title": meta.get("title", ""),
                    "summary": meta.get("summary", ""),
                    "message_count": int(msg_count),
                    "participant_count": int(meta.get("participant_count", 0) or 0),
                    "channel_id": meta.get("channel_id", ""),
                    "workspace": meta.get("workspace_name", ""),
                    "key_topics": meta.get("key_topics", []),
                    "timestamp": meta.get("timestamp", ""),
                    "last_seen": row.get("last_seen", ""),
                }
            )

    print(f"  {len(threads)} threads with valid metadata", flush=True)

    # Stats
    total_threads = len(threads)
    total_messages = sum(t["message_count"] for t in threads)
    avg_messages = total_messages / total_threads if total_threads else 0
    avg_participants = (
        sum(t["participant_count"] for t in threads) / total_threads
        if total_threads
        else 0
    )
    max_messages = max(t["message_count"] for t in threads) if threads else 0

    # Size distribution - count properly
    large = sum(1 for t in threads if t["message_count"] >= 50)
    medium = sum(1 for t in threads if 20 <= t["message_count"] < 50)
    small = sum(1 for t in threads if 5 <= t["message_count"] < 20)
    tiny = sum(1 for t in threads if t["message_count"] < 5)

    size_data = {
        "Large (50+)": large,
        "Medium (20-49)": medium,
        "Small (5-19)": small,
        "Tiny (<5)": tiny,
    }

    # Monthly activity - count per month
    monthly = Counter()
    for t in threads:
        ts = t.get("timestamp") or t.get("last_seen")
        if ts:
            try:
                if "T" in ts:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                else:
                    dt = datetime.fromisoformat(ts)
                monthly[dt.strftime("%Y-%m")] += 1
            except Exception:
                pass  # malformed timestamp, skip

    # Channel distribution
    channels = Counter(t["channel_id"] for t in threads if t["channel_id"])

    # Topic analysis
    topics = Counter()
    for t in threads:
        for topic in t.get("key_topics", []):
            if topic and topic.strip():
                topics[topic.lower().strip()] += 1

    # Top threads
    top_threads = sorted(threads, key=lambda x: x["message_count"], reverse=True)[:25]

    print("generating charts...", flush=True)

    # 1. Size distribution bar chart
    max_size = max(size_data.values()) if size_data else 1
    fig_size = go.Figure(
        data=[
            go.Bar(
                x=list(size_data.values()),
                y=list(size_data.keys()),
                orientation="h",
                text=[
                    f"{v} ({v / total_threads * 100:.1f}%)" for v in size_data.values()
                ],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white"),
                marker_color="#58a6ff",
            )
        ]
    )
    fig_size.update_layout(
        template=None,
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#c9d1d9", family="monospace", size=12),
        height=250,
        margin=dict(l=130, r=30, t=10, b=40),
        xaxis=dict(
            title="threads",
            range=[0, max_size * 1.1],
            gridcolor="#21262d",
            zerolinecolor="#21262d",
        ),
        yaxis=dict(type="category", gridcolor="#21262d", zerolinecolor="#21262d"),
        showlegend=False,
    )

    # 2. Monthly trend
    months = sorted(monthly.keys())
    max_monthly = max(monthly.values()) if monthly else 1
    fig_monthly = go.Figure(
        data=[
            go.Bar(
                x=months,
                y=[monthly[m] for m in months],
                text=[monthly[m] for m in months],
                textposition="outside",
                textfont=dict(color="#c9d1d9"),
                marker_color="#58a6ff",
            )
        ]
    )
    fig_monthly.update_layout(
        template=None,
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#c9d1d9", family="monospace", size=12),
        height=350,
        margin=dict(l=50, r=20, t=40, b=60),
        xaxis=dict(
            title="month", tickangle=-45, gridcolor="#21262d", zerolinecolor="#21262d"
        ),
        yaxis=dict(
            title="threads",
            range=[0, max_monthly * 1.25],
            gridcolor="#21262d",
            zerolinecolor="#21262d",
        ),
    )

    # 3. Top channels
    top_channels = channels.most_common(8)
    max_channel = top_channels[0][1] if top_channels else 1
    fig_channels = go.Figure(
        data=[
            go.Bar(
                x=[c[1] for c in top_channels],
                y=[c[0] for c in top_channels],
                orientation="h",
                text=[f"{c[1]:,}" for c in top_channels],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white"),
                marker_color="#3fb950",
            )
        ]
    )
    fig_channels.update_layout(
        template=None,
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#c9d1d9", family="monospace", size=12),
        height=300,
        margin=dict(l=130, r=30, t=10, b=40),
        xaxis=dict(
            title="threads",
            range=[0, max_channel * 1.1],
            gridcolor="#21262d",
            zerolinecolor="#21262d",
        ),
        yaxis=dict(
            type="category",
            autorange="reversed",
            gridcolor="#21262d",
            zerolinecolor="#21262d",
        ),
    )

    # 4. Top topics
    top_topics = topics.most_common(15)
    max_topic = top_topics[0][1] if top_topics else 1
    fig_topics = go.Figure(
        data=[
            go.Bar(
                x=[t[1] for t in top_topics],
                y=[t[0] for t in top_topics],
                orientation="h",
                text=[t[1] for t in top_topics],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white"),
                marker_color="#f0883e",
            )
        ]
    )
    fig_topics.update_layout(
        template=None,
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#c9d1d9", family="monospace", size=12),
        height=450,
        margin=dict(l=220, r=30, t=10, b=40),
        xaxis=dict(
            title="mentions",
            range=[0, max_topic * 1.1],
            gridcolor="#21262d",
            zerolinecolor="#21262d",
        ),
        yaxis=dict(
            type="category",
            autorange="reversed",
            gridcolor="#21262d",
            zerolinecolor="#21262d",
        ),
    )

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Slack Thread Analytics</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
            background: #0d1117;
            color: #c9d1d9;
            font-size: 14px;
        }}
        h1 {{ color: #58a6ff; font-weight: 400; }}
        h2 {{ color: #8b949e; font-weight: 400; margin-top: 40px; border-bottom: 1px solid #21262d; padding-bottom: 8px; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 25px 0;
        }}
        .stat {{
            background: #161b22;
            border: 1px solid #21262d;
            padding: 16px;
            border-radius: 6px;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: 600;
            color: #58a6ff;
        }}
        .stat-label {{
            color: #8b949e;
            margin-top: 4px;
            font-size: 12px;
        }}
        .chart {{
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 6px;
            margin: 15px 0;
            overflow: hidden;
        }}
        .chart > div {{
            width: 100% !important;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 6px;
            overflow: hidden;
            font-size: 13px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #21262d;
        }}
        th {{
            background: #21262d;
            color: #8b949e;
            font-weight: 500;
        }}
        tr:hover td {{
            background: #1c2128;
        }}
        .summary {{
            color: #8b949e;
            font-size: 12px;
            max-width: 350px;
        }}
        .num {{ text-align: right; color: #58a6ff; }}
        .meta {{ color: #666; font-size: 11px; margin-top: 30px; }}
    </style>
</head>
<body>
    <h1>slack thread analytics</h1>
    <p style="color: #8b949e;">analysis of {total_threads:,} AI-summarized threads from prefect community slack</p>

    <div class="stats">
        <div class="stat">
            <div class="stat-value">{total_threads:,}</div>
            <div class="stat-label">threads</div>
        </div>
        <div class="stat">
            <div class="stat-value">{total_messages:,}</div>
            <div class="stat-label">total messages</div>
        </div>
        <div class="stat">
            <div class="stat-value">{avg_messages:.1f}</div>
            <div class="stat-label">avg msgs/thread</div>
        </div>
        <div class="stat">
            <div class="stat-value">{max_messages}</div>
            <div class="stat-label">max messages</div>
        </div>
        <div class="stat">
            <div class="stat-value">{avg_participants:.1f}</div>
            <div class="stat-label">avg participants</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len(channels)}</div>
            <div class="stat-label">unique channels</div>
        </div>
    </div>

    <h2>threads per month</h2>
    <div class="chart" id="chart-monthly"></div>

    <h2>thread size distribution</h2>
    <div class="chart" id="chart-size"></div>
    <p style="color: #8b949e; font-size: 12px;">
        large (50+ msgs): {large} &nbsp;|&nbsp;
        medium (20-49): {medium} &nbsp;|&nbsp;
        small (5-19): {small} &nbsp;|&nbsp;
        tiny (&lt;5): {tiny}
    </p>

    <h2>top channels</h2>
    <div class="chart" id="chart-channels"></div>

    <h2>top topics</h2>
    <p style="color: #8b949e; font-size: 12px;">key topics extracted from thread summaries</p>
    <div class="chart" id="chart-topics"></div>

    <h2>most active threads</h2>
    <table>
        <thead>
            <tr>
                <th>title</th>
                <th class="num">msgs</th>
                <th class="num">people</th>
                <th>summary</th>
            </tr>
        </thead>
        <tbody>
"""
    for t in top_threads:
        title = (t["title"] or "")[:55]
        if len(t["title"]) > 55:
            title += "..."
        summary = (t["summary"] or "")[:120]
        if len(t["summary"]) > 120:
            summary += "..."
        full_summary = (t["summary"] or "").replace('"', "&quot;")
        html += f"""            <tr>
                <td title="{(t["title"] or "").replace('"', "&quot;")}">{title}</td>
                <td class="num">{t["message_count"]}</td>
                <td class="num">{t["participant_count"]}</td>
                <td class="summary" title="{full_summary}">{summary}</td>
            </tr>
"""

    html += f"""        </tbody>
    </table>

    <p class="meta">generated {datetime.now().strftime("%Y-%m-%d %H:%M")} from turso</p>

    <script>
        Plotly.newPlot('chart-monthly', {fig_monthly.to_json()}.data, {fig_monthly.to_json()}.layout);
        Plotly.newPlot('chart-size', {fig_size.to_json()}.data, {fig_size.to_json()}.layout);
        Plotly.newPlot('chart-channels', {fig_channels.to_json()}.data, {fig_channels.to_json()}.layout);
        Plotly.newPlot('chart-topics', {fig_topics.to_json()}.data, {fig_topics.to_json()}.layout);
    </script>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Analyze Slack thread data")
    parser.add_argument("--output", "-o", default="report.html", help="Output file")
    parser.add_argument("--open", action="store_true", help="Open in browser")
    args = parser.parse_args()

    try:
        settings = Settings()  # type: ignore
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    html = generate_report(settings)
    with open(args.output, "w") as f:
        f.write(html)
    print(f"wrote {args.output}")

    if args.open:
        import webbrowser

        webbrowser.open(args.output)


if __name__ == "__main__":
    main()
