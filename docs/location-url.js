// A station link is distinct from the project's general 360° entry point.
function validUnitTourURL(value) {
  if (typeof value !== 'string' || !value.trim()) return '';
  let url;
  try { url = new URL(value.trim()); } catch { return ''; }
  if (url.protocol !== 'https:' || url.username || url.password || url.port ||
      !['alhabeebconst.com', 'www.alhabeebconst.com'].includes(url.hostname)) return '';
  const parts = url.pathname.split('/').filter(Boolean);
  if (parts[0]?.toLowerCase() !== 'virtual-tour') return '';
  const hash = url.hash.slice(1).trim();
  const sceneParam = [...url.searchParams.entries()].some(([key, val]) =>
    /^(?:start_?)?(?:scene|panorama|pano|room|node|hotspot|media|waypoint)(?:[_-]?(?:id|index|name))?$|^(?:id|s|vroom)$/i.test(key) && val.trim());
  const nestedViewer = parts.length >= 3 && parts[1].toLowerCase() === 'viewer' &&
    !/^index(?:\.[a-z0-9]+)?$/i.test(parts.at(-1)) && !/\.(?:png|jpe?g|webp|js|css|xml|json)$/i.test(parts.at(-1));
  return (hash || sceneParam || nestedViewer) ? url.href : '';
}
