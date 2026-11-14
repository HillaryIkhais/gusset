# GUSSET — Motion Canvas Animation Sequences

Custom TypeScript animations for the GUSSET demo video. Requires Node.js and Motion Canvas (`npm install @motion-canvas/core @motion-canvas/2d`). Render with `npx motion-canvas build`.

## Usage

```bash
cd production/motion-canvas
npm install @motion-canvas/core @motion-canvas/2d
npx motion-canvas build scenes.ts
```

## Scenes

1. **`diagnosticMatrix`** — 2×2 matrix fills cell by cell (TP=0, FA=1, FR=1, TN=7)
2. **`headlineNumbers`** — Judge accuracy 77.8% vs baseline 88.9%, sensitivity 0.0%
3. **`caseCards`** — Two contrasting case cards slide in
4. **`titleReveal`** — "GUSSET" with subtitle fade-in

Each scene exports a React component compatible with Motion Canvas.
