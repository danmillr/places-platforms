# Creative Forms: Collecting and Revisualizing User Input

**Status: Shell.** Structure and pattern are here; working code is not yet built.

## What you will build

A static site with a form (or drawing surface, or audio uploader, or any expressive input) that saves each submission to a lightweight backend. The same site reads back all submissions and re-renders them as a visualization: a map, a scatter, a gallery, a marquee.

## Prerequisites

- A code editor and a GitHub account
- A free account on one of: JSONBin, Firebase, Supabase, or Google Sheets (via a script)
- No node, no build step

## The pattern

Every "form on a static site" solution has three parts:

1. **A collector.** Something on the page that produces structured data. A `<form>`, a canvas drawing serialized to JSON, an audio blob, a set of geolocated tags.
2. **A store.** A tiny cloud database endpoint that you write to and read from. Not a full backend.
3. **A reader.** Code that fetches everything currently stored and turns it into a view.

## Backend options

| Option | Read + Write from browser | Free tier | Auth story | When to use |
|---|---|---|---|---|
| **JSONBin.io** | Yes | 10k requests/mo | API key restricted by domain | Prototypes, small classes, no auth |
| **Firebase Realtime DB** | Yes | Generous | Anonymous auth built in | Live updates across visitors |
| **Supabase** | Yes | Generous | Row-level security | If you know SQL |
| **Google Sheets via Apps Script** | Yes (via webhook) | Free | None (public sheet) | Non-technical review of submissions |
| **Netlify Forms** | Yes (write only) | 100 submissions/mo | Netlify auth | If already on Netlify, but read-back requires their API |

For a first pass, use JSONBin. Swap for Firebase if you need live updates.

## Data schema

Design your record before building the form. Every submission should include:

```json
{
  "id": "auto-generated",
  "timestamp": "2026-04-10T14:22:00Z",
  "user_token": "anonymous-random-string-in-localStorage",
  "content": { ... your form fields ... },
  "location": { "lat": 40.72, "lon": -74.00 },
  "metadata": { "user_agent": "...", "session": "..." }
}
```

The `user_token` is a random string you generate once per browser and save in `localStorage`. That way you can group submissions from the same visitor without a login.

## Walkthrough (outline)

1. **Form HTML** with named inputs. Include hidden inputs for `timestamp` and `user_token`.
2. **Submit handler** that assembles the record and POSTs to your backend.
3. **Loader** on page load that GETs all records and calls a render function.
4. **Render function** that turns the records array into whatever visualization you want (map layer, scatter, gallery, list).
5. **Deduplication or moderation** if the input is public. At minimum, cap length and rate-limit by `user_token`.

## Extensions

- **Drawing on a canvas** that saves as an SVG path array. Replay every drawing on load.
- **Audio memo** with `MediaRecorder`, uploaded to Firebase Storage, replayed in a gallery.
- **Map pin drop** where the form is a click on a MapLibre map.
- **Time-lapse of contributions** by animating features in submission order.

## Common pitfalls

- **Exposed API keys.** JSONBin keys embedded in JS are visible to anyone. Restrict the key to a single bin and to your domain. For anything you cannot afford to be spammed, use Firebase with anonymous auth and security rules.
- **CORS on Google Sheets.** Apps Script web apps need `doPost` and correct `ContentService` output. Test with `curl` before wiring the client.
- **Growing bin size.** JSONBin caps individual bin size. If your class fills it, migrate to Firebase or paginate to multiple bins.
- **Trust.** Never trust submitted data. Sanitize before rendering. If you display user text, escape HTML.
