/** A4 landscape width at 96 DPI (297mm). */
export const A4_LANDSCAPE_WIDTH_PX = 1122;

export const EXPORT_SHEET_PADDING = '10mm';

/**
 * Wait for fonts to finish loading and let the browser settle one paint
 * cycle before html2canvas captures. Fixes text appearing shifted/misaligned
 * in exported images vs. live preview.
 */
export async function waitForExportReady() {
  if (document.fonts && document.fonts.ready) {
    await document.fonts.ready;
  }
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

/** Cap at 2 for speed; layout is already print width. */
export function getCaptureScale(elementWidth) {
  if (!elementWidth || elementWidth <= 0) return 2;
  return Math.min(2, Math.ceil(A4_LANDSCAPE_WIDTH_PX / elementWidth));
}

export function getPdfImageDimensions(doc, imgData, margin = 8) {
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const props = doc.getImageProperties(imgData);
  const availW = pageW - margin * 2;
  const availH = pageH - margin * 2;
  let w = availW;
  let h = (props.height * w) / props.width;
  if (h > availH) {
    h = availH;
    w = (props.width * h) / props.height;
  }
  return { x: margin, y: margin, w, h };
}

export function downloadCanvasAsImage(canvas, filename) {
  const link = document.createElement('a');
  link.download = filename;
  link.href = canvas.toDataURL('image/png');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}