# Logistics dashboard: setup and toolkit

Do the steps in order. Tools come last on purpose: a tool can't tell you what to measure.

## Step 0: before any tool (about 10 minutes)

Write down and send to Claude:
1. **Three decisions** the dashboard must help you make, e.g. "which carrier to escalate
   this week", "which routes are losing money", "do we need extra drivers on Fridays".
2. **Who reads it, and how often** (you daily? a manager weekly? on a phone?).
3. **The data:** the CSV files themselves, or at least their column names + 20 rows each.

Claude will then profile the CSVs before designing anything: what one row means
(shipment, order line, stop?), duplicates, date formats and time zones, blanks, status
codes, and how the files join.

## Step 1: toolkit

| Need | Recommended | Alternatives | Notes |
| --- | --- | --- | --- |
| Clean and join the CSVs | **Power Query** (inside Excel) | Python/pandas (Claude can do this), Power BI's Power Query | Clean once, refresh forever |
| Measures and KPIs | **Excel Data Model + DAX measures** or PivotTables | `SUMIFS`/dynamic arrays; Power BI | See the build-mode guide in the critical-thinking skill |
| Build the dashboard | **Excel (Microsoft 365 desktop)** | **Power BI Desktop** (free, Windows only) if you need maps, sharing and a mobile *viewing* app | Check your Excel version: some functions need Microsoft 365 |
| Layout sketch | **Paper or a blank Excel sheet** | Figma | Figma is optional; see below |
| Maps (routes, depots) | Power BI map visuals or Excel 3D Maps | | Needs clean location fields (postcode/lat-long) |
| Version control | This GitHub repo | | Keep the queries, notes and reviews; keep raw data private |

Typical logistics KPIs to choose from (pick the ones your three decisions need):
on-time / on-time-in-full %, median and 90th-percentile lead time, cost per shipment /
per drop / per kg, failed or re-attempted deliveries, carrier performance, vehicle
utilisation. Prefer medians and percentiles over averages for times: delays skew averages.

## Step 2 (optional): Figma via MCP

Is Figma worth it here? Usually not for an Excel or Power BI dashboard, because neither
can import a Figma design. You would only be drawing a mock-up that someone then
rebuilds by hand. Figma becomes useful if the dashboard will be a **web page or app**, or
you want a polished mock-up to agree the layout with others first.

If you do want it:

- **In the Claude app / claude.ai:** connect Figma at
  https://claude.ai/customize/connectors, then start a new chat or session.
  Connectors are read when a session starts.
- **In Claude Code on your laptop:**
  ```
  claude mcp add --transport http figma https://mcp.figma.com/mcp
  ```
  Then run `claude`, type `/mcp`, choose figma and sign in to Figma in the browser.
  Add `--scope user` to the `claude mcp add` command to make it available in every
  project. A server added this way lives on your laptop only. It does not carry over
  to cloud sessions; those use the claude.ai connector.
- **Read vs write:** Figma documents a `use_figma` tool on the remote server that can
  write to the canvas (https://developers.figma.com/docs/figma-mcp-server/write-to-canvas).
  Third-party sources describe write-to-canvas as a beta that may become paid. Check
  Figma's current guide for seat and plan limits before relying on it.

## Step 3: drive it from your phone with Remote Control

Remote Control runs Claude Code **on your laptop** and lets you continue that session
from the Claude mobile app or claude.ai/code. Your files, local MCP servers (including
Figma) and tools stay on the laptop.
Source: https://code.claude.com/docs/en/remote-control

1. On the laptop, install Claude Code and sign in with your claude.ai account (`claude`,
   then `/login`). It needs a Pro, Max, Ultra, Team or Enterprise plan; API keys are not
   supported.
2. Open a terminal in the project folder (e.g. your clone of this repo) and run:
   ```
   claude remote-control
   ```
   Accept the prompts, then press the space bar to show a QR code. Or start an
   interactive session with `claude --remote-control "Logistics dashboard"`. From
   inside a session you're already in, type `/remote-control`.
   (Claude Desktop app: type `/remote-control` in a Code-tab session.)
3. On your phone, scan the QR code, or open the Claude app → **Code** and pick the
   session (computer icon, green dot).
4. Keep the laptop awake and the terminal open: if it sleeps, the session stops.

Limits:
- This drives Claude Code: files, scripts, Python, generating `.xlsx` files. It does not
  click around inside the Excel window. For that, Claude would need computer use
  through the Claude desktop app.
- Review the finished dashboard on a real screen; a phone is too small to judge one.

## Step 4: build, then challenge

Claude builds → you check each decision is answered by one visual and the totals match
the raw CSV → the `critical-thinker` agent challenges the measures → the
`content-reviewer` agent scores it → fix → sign off.
