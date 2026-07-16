# Collective Traces: Persistent Marks on a Shared Page

**Status: Shell.** Structure and pattern are here; working code is not yet built.

## What you will build

A single-page site tied to a POPS or other site. Visitors can leave a small persistent mark. In the reference design, that mark is a single pixel changed on a background image, but the same pattern supports a dot on a canvas, a short text pinned to a spot, or an audio blob tied to a coordinate.

The state is shared: whatever any visitor draws, every other visitor sees.

## Prerequisites

- A code editor
- A free Firebase or Supabase project for shared state
- A background image (photo of your site, plan drawing, satellite crop) with a known pixel resolution

## The pattern

Three pieces:

1. **A canvas** overlaid on the background image, or on a blank surface.
2. **A shared store** that holds an append-only list of marks: `{ x, y, color, timestamp, user_token }`.
3. **A live sync** so that when one visitor draws, the others see it.

## Data model

```json
{
  "marks": [
    { "x": 234, "y": 512, "color": "#3C4ED6", "t": 1710000000, "u": "abc123" },
    ...
  ]
}
```

Firebase Realtime Database is a good fit because it pushes updates to every connected client without polling. Supabase Realtime works the same way.

## Walkthrough (outline)

1. **HTML** with a background image and an absolutely-positioned `<canvas>` matching its size.
2. **Draw handler.** On `click` (or `mousedown` for drag), compute the pixel in image coordinates, draw one pixel to the canvas, and push the mark to the store.
3. **Sync.** Subscribe to the store. On any new mark, draw it to the canvas.
4. **Replay on load.** Read all existing marks and draw them in order.
5. **Rate limit.** One mark per second per user_token. Enforce client-side and again with security rules.

## Firebase snippet (client-side)

```js
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getDatabase, ref, push, onChildAdded } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

const app = initializeApp({ /* config */ });
const db = getDatabase(app);
const marksRef = ref(db, "marks");

// write
canvas.addEventListener("click", e => {
  const { x, y } = pixelFromEvent(e);
  push(marksRef, { x, y, color: pickColor(), t: Date.now(), u: userToken });
});

// read + subscribe
onChildAdded(marksRef, snap => drawMark(snap.val()));
```

## Variants

- **Text pins** instead of pixels. A short string appears at the click point. Same data model, add a `text` field.
- **Audio memos** anchored to coordinates. Upload the audio blob to Firebase Storage, save the download URL in the mark.
- **Fading traces.** On render, use `t` to fade older marks. Newer marks are opaque, older ones are faint.
- **Local plans.** Instead of an image, use a MapLibre map. Marks are lat/lng points in a `geojson` source.

## Ethical and technical considerations

- **Content moderation.** Anything the public can write, someone will try to break. Provide an admin-only URL that can hide or delete marks. Build it before you share the link.
- **User anonymity.** The `user_token` in localStorage is not privacy-strong. Do not tie it to identity. If you need real identity, use Firebase Auth.
- **Cost.** Firebase's free tier holds 100 concurrent connections. If a class of 30 hits your site at once from different networks, that fits. If it goes viral, disable writes.
- **Backup.** Export the database once a day. Anything user-generated can vanish if the DB is deleted or migrated.
- **Consent.** If you use this as a research method, get IRB or equivalent approval before publishing.

## Common pitfalls

- **Canvas coordinate math.** `getBoundingClientRect` accounts for CSS scaling. Map from client coords to image pixel coords using the ratio.
- **Retina scaling.** Set `canvas.width` and `canvas.height` to the image's natural size, then style the CSS width to fit. Otherwise your pixel is a fuzzy blob.
- **Firebase security rules.** The default rules block reads and writes after 30 days. Write explicit rules before going live.
- **Race conditions on replay.** If two clients load simultaneously and both push a mark, both should render both. `onChildAdded` handles this if you subscribe before the initial page render, not after.
