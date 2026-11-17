export function revokeInactiveImagePreviewUrls(
  ownedUrls,
  activeUrl,
  revokeObjectURL,
) {
  for (const url of ownedUrls) {
    if (url === activeUrl) continue;
    revokeObjectURL(url);
    ownedUrls.delete(url);
  }
}
