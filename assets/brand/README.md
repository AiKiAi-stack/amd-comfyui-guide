# Brand mark

`mark.svg` and `mark-light.svg` are the same mark in two colourways: the ComfyUI node mark on the left, the AMD wordmark on the right, joined by a link drawn the way ComfyUI draws an edge between two nodes.

That is also the argument of the guide. AMD cards do run ComfyUI graphs, and the link is the part this repository measured.

## Using it

- `viewBox="0 0 258.4 100"`, no embedded raster, no fonts. It scales from a favicon to a poster.
- Dark ground: gold `#e2bd4b` for the node mark and the link, bone `#f3eee2` for the AMD wordmark. Light ground: `#b58b1e` and ink `#12100c`.
- Both READMEs load the pair through `<picture>` with `prefers-color-scheme` at 220 px wide, so the mark reads on either GitHub theme.

## Where the geometry came from

- ComfyUI node mark: traced from the official logo supplied with the workflow inputs (`workflows/input/ModelLibrary_392b4f8b16d3_comfy_logo_blue.png`). The silhouette is a 46-point path, which is smooth enough at README size and keeps the file at about 1.4 KB.
- AMD wordmark: the public simple-icons path (CC0).
- The link and its socket dot are drawn for this mark; they are not part of either logo.

Both logos are trademarks of their owners and sit outside the MIT licence. See `THIRD_PARTY_NOTICES.md`.
