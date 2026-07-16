# Text Game with Behavioral Analytics

**Status: Shell.** Structure and pattern are here; working code is not yet built.

## What you will build

A browser-based text adventure. The student authors the game logic (nodes and choices) in a data file. As players play, the site captures every event (which node they entered, how long they stayed, which choice they made). At the end, the site shows the player a personalized summary visualization built from their own path plus everyone else's.

## Prerequisites

- A code editor
- A backend for storing sessions (Firebase, Supabase, or JSONBin all work; Firebase is best for a live class)
- D3 or a lighter charting library for the end-of-game visualization

## Data model

**Game definition (author-authored):**

```json
{
  "start": "prologue",
  "nodes": {
    "prologue": {
      "text": "You arrive at the plaza. It is empty except for a bench.",
      "choices": [
        { "label": "Sit on the bench", "goto": "bench" },
        { "label": "Look for someone", "goto": "search" }
      ]
    },
    "bench": { "text": "...", "choices": [...] }
  }
}
```

**Session log (captured):**

```json
{
  "session_id": "uuid",
  "start_time": "...",
  "events": [
    { "t": 0, "type": "enter", "node": "prologue" },
    { "t": 14.2, "type": "choose", "node": "prologue", "choice_idx": 0, "goto": "bench" },
    { "t": 14.2, "type": "enter", "node": "bench" },
    ...
    { "t": 220.5, "type": "end", "node": "epilogue" }
  ]
}
```

Session ends when the player hits an end node, closes the tab (use `beforeunload`), or is idle beyond a threshold.

## Walkthrough (outline)

### 1. Game engine

Pure client-side state machine:

```js
let state = { node: game.start, startedAt: Date.now(), events: [] };

function enter(nodeId) {
  state.events.push({ t: elapsed(), type: "enter", node: nodeId });
  state.node = nodeId;
  render();
}

function choose(idx) {
  const node = game.nodes[state.node];
  const choice = node.choices[idx];
  state.events.push({ t: elapsed(), type: "choose", node: state.node, choice_idx: idx, goto: choice.goto });
  enter(choice.goto);
}
```

### 2. Persistence

On each state change, sync `state.events` to your backend. Buffer to reduce writes:

```js
let flushTimer;
function scheduleFlush() {
  clearTimeout(flushTimer);
  flushTimer = setTimeout(flushToServer, 2000);
}
```

Use `navigator.sendBeacon` in a `beforeunload` handler to catch dropouts.

### 3. End-of-game visualization

When the player reaches an end node, replace the game view with a summary panel. Suggested visualizations:

- **Your path.** A vertical timeline of nodes visited, sized by dwell time.
- **Time per choice.** A small bar chart comparing your dwell time at each node to the class median.
- **The tree.** A force-directed diagram of the game graph, with your path highlighted in one color and the aggregate flow (thicker edges = more players) underneath.
- **Sankey.** Class-level Sankey of node-to-node transitions, with your ribbon highlighted.
- **Dwell heatmap.** X = nodes in order visited, Y = seconds spent, color = choice made. A scarf plot of the session.

### 4. Aggregate visualization (post-play)

A separate `/aggregate` view (or the same summary panel) reads all sessions and shows patterns:

- Which choices are most common at each node
- Median session length
- Common paths visualized as a Sankey
- Node abandonment rates

## Extensions

- **Inject location.** Only progress to certain nodes if the player is inside a POPS or near a specific place. (See `geolocation-zones/`.)
- **Multiplayer.** Show a live count of players at each node. Nodes with 3+ players unlock a group option.
- **Multi-modal input.** Nodes can require an image upload, a drawing, or a short audio recording. Store the artifacts and show them in the aggregate view. (See `creative-forms/`.)
- **Adaptive difficulty.** The game reads the aggregate stats and steers slower players toward shorter branches.

## Common pitfalls

- **Losing sessions.** Players close tabs. Use `sendBeacon` on `beforeunload` to flush the final buffer.
- **Cheating with the back button.** If your game is a science project, disable browser navigation with `history.pushState` and a `popstate` handler.
- **Firebase costs.** A game with 100 players and 20 choices each is 2000 events. Fine on the free tier. Ten thousand players will not be. Budget accordingly.
- **Overinterpreting dwell time.** Dwell = time on node, not time reading. Some players tab away. Cap dwell at a max (e.g., 5 minutes) before treating it as a signal.
- **Consent.** If you plan to publish player behavior data, tell them upfront. A one-sentence notice on the start screen is enough for coursework.
