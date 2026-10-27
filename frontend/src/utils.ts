export function getInitials(name: string) {
  const names = name.split(' ')
  let initials = ''
  for (let i = 0; i < names.length; i++) {
    initials += names[i].charAt(0).toLocaleUpperCase()
  }
  return initials
}

export function formatSize(size: string | number) {
  const num = Number(size)
  if (isNaN(num)) return size
  if (num < 1024) return `${num} B`
  if (num < 1024 ** 2) return `${(num / 1024).toFixed(1)} KB`
  if (num < 1024 ** 3) return `${(num / 1024 ** 2).toFixed(1)} MB`
  return `${(num / 1024 ** 3).toFixed(1)} GB`
}

export function diffDisplay(oldPath: string, newPath: string): string {
    if (oldPath === newPath)
        return `<div class="diffLine"><span class="noop">${escapeHtml(oldPath)}</span> <span class="same">(no changes)</span></div>`

    let start = 0, endOld = oldPath.length, endNew = newPath.length

    while (start < endOld && start < endNew && oldPath[start] === newPath[start]) start++
    while (endOld > start && endNew > start && oldPath[endOld - 1] === newPath[endNew - 1]) { endOld--; endNew-- }

    const esc = escapeHtml
    const prefix = esc(oldPath.slice(0, start))
    const suffix = esc(oldPath.slice(endOld))
    const removed = esc(oldPath.slice(start, endOld))
    const added = esc(newPath.slice(start, endNew))

    return `
    <div class="diffLine">${prefix}<span class="removedDiff">${removed}</span>${suffix}</div>
    <div class="diffLine">${prefix}<span class="addedDiff">${added}</span>${suffix}</div>
  `
}

function escapeHtml(s: string) {
    return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!))
}

export async function runBatch(keys: string[],  requestFn: (key: string) => Promise<unknown>): Promise<void> {
  const results = await Promise.allSettled(keys.map(key => requestFn(key)))
  const errors = results.filter(result => result.status === 'rejected')
  if (errors.length) {
    throw new Error(`${errors.length} of ${keys.length} requests failed`)
  }
}

export type DownloadType = "direct" | "torrent" | "usenet";

const extensionMap: Record<string, DownloadType> = {
  // Ebook formats
  epub: "direct",
  pdf: "direct",
  mobi: "direct",
  azw: "direct",
  azw3: "direct",
  azw4: "direct",
  kfx: "direct",
  prc: "direct",
  fb2: "direct",
  djvu: "direct",
  djv: "direct",
  txt: "direct",
  rtf: "direct",
  doc: "direct",
  docx: "direct",
  odt: "direct",
  html: "direct",
  htm: "direct",
  xhtml: "direct",
  md: "direct",

  // Comics / manga
  cbz: "direct",
  cbr: "direct",
  cb7: "direct",
  cbt: "direct",
  cba: "direct",

  // Legacy / specialized ebooks
  lit: "direct",
  lrf: "direct",
  lrx: "direct",
  pdb: "direct",
  pml: "direct",
  pmlz: "direct",
  rb: "direct",
  imp: "direct",
  oeb: "direct",
  oebzip: "direct",
  tr2: "direct",
  tr3: "direct",
  tcr: "direct",
  zbf: "direct",
  bgl: "direct",
  chm: "direct",
  xps: "direct",
  oxps: "direct",
  ps: "direct",
  eps: "direct",
  brf: "direct",
  brl: "direct",

  // Archives containing ebooks
  zip: "direct",
  rar: "direct",
  "7z": "direct",
  tar: "direct",
  gz: "direct",

  // Torrent
  torrent: "torrent",

  // Usenet
  nzb: "usenet",
};

export function getDownloadType(file: File): DownloadType | null {
  const extension = file.name.toLowerCase().split(".").pop();

  if (!extension) return null;

  return extensionMap[extension] ?? null;
}