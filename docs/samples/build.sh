#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$ROOT_DIR/pdf_output"
DIAGRAM_DIR="$ROOT_DIR/diagrams"

mkdir -p "$OUT_DIR" "$DIAGRAM_DIR"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required tool: $1"; exit 1; }
}

need pandoc
need tectonic
need mmdc

echo "[1/3] Rendering Mermaid diagrams..."
cat > "$DIAGRAM_DIR/incident-timeline.mmd" <<'EOF'
flowchart TD
  A[09:03 Alert Triggered] --> B[09:07 On-call Acknowledged]
  B --> C[09:12 Root Cause Isolated]
  C --> D[09:30 Fix Deployed]
  D --> E[09:32 Service Stable]
EOF

mmdc -i "$DIAGRAM_DIR/incident-timeline.mmd" -o "$DIAGRAM_DIR/incident-timeline.png" -t default -b transparent

echo "[2/3] Preparing markdown with rendered diagram..."
TMP_MD="$ROOT_DIR/incident-report-001.rendered.md"
awk '
  BEGIN{inside=0}
  /```mermaid/{inside=1; print "![Incident timeline](./diagrams/incident-timeline.png)"; next}
  /```/ && inside==1 {inside=0; next}
  inside==0 {print}
' "$ROOT_DIR/incident-report-001.md" > "$TMP_MD"

echo "[3/3] Converting markdown -> PDF..."
for md in "$ROOT_DIR"/*.md "$TMP_MD"; do
  base="$(basename "$md")"
  [[ "$base" == "README.md" ]] && continue
  [[ "$base" == "build.sh" ]] && continue
  out="$OUT_DIR/${base%.md}.pdf"
  pandoc "$md" --pdf-engine=tectonic -o "$out"
  echo "  - generated $(basename "$out")"
done

rm -f "$TMP_MD"
echo "Done. PDFs in: $OUT_DIR"
