'use strict';

/* ====== SVG icons ====== */
const ICON_COPY  = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
const ICON_CHECK = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
const ICON_DOWN  = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>';
const ICON_RIGHT = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>';

/* ====== Source metadata ====== */
const SOURCES = [
  { id: 'gtfobins',         label: 'GTFOBins',             icon: '🐚', color: '#ff9e64', noNav: true },
  { id: 'lolbas',           label: 'LOLBAS',               icon: '🪟', color: '#e0af68', noNav: true },
  { id: 'bloodhound',       label: 'BloodHound',           icon: '🩸', color: '#f7768e' },
  { id: 'bloodyad',         label: 'bloodyAD',             icon: '🩸', color: '#db4b4b' },
  { id: 'certipy',          label: 'Certipy',              icon: '📜', color: '#f7768e' },
  { id: 'goexec',           label: 'goexec',               icon: '⚡', color: '#9ece6a' },
  { id: 'gopacket',         label: 'GoPacket',             icon: '🐹', color: '#9ece6a' },
  { id: 'hacktricks',       label: 'HackTricks',           icon: '🤖', color: '#f7768e' },
  { id: 'hacktricks-cloud', label: 'HackTricks Cloud',     icon: '☁️',  color: '#7aa2f7' },
  { id: 'hardware-att',     label: 'HardwareAllTheThings', icon: '🔌', color: '#e0af68' },
  { id: 'impacket',         label: 'Impacket',             icon: '📦', color: '#2ac3de' },
  { id: 'internal-att',     label: 'InternalAllTheThings', icon: '🏰', color: '#bb9af7' },
  { id: 'ligolo-ng',        label: 'Ligolo-ng',            icon: '🔀', color: '#2ac3de' },
  { id: 'mimikatz',         label: 'Mimikatz',             icon: '🐱', color: '#f7768e' },
  { id: 'msfvenom',         label: 'msfvenom',             icon: '💣', color: '#bb9af7' },
  { id: 'netexec',          label: 'NetExec Wiki',         icon: '🔧', color: '#9ece6a' },
  { id: 'osai-research',    label: 'OSAI Research',        icon: '🤖', color: '#bb9af7' },
  { id: 'patt',             label: 'PayloadsAllTheThings', icon: '💥', color: '#ff9e64' },
  { id: 'rubeus',           label: 'Rubeus',               icon: '🎟️', color: '#ff9e64' },
  { id: 'sliver',           label: 'Sliver C2',            icon: '🐍', color: '#f7768e' },
  { id: 'hacker-recipes',   label: 'The Hacker Recipes',  icon: '🍳', color: '#7dcfff' },
];

const _navCache   = {};
const _activeSource  = document.body.dataset.source || '';
const _currentPath   = document.body.dataset.pageUrl || '';

/* ====== Session state helpers ====== */
function _skey(k) { return 'pt_' + k; }
function _isOpen(k)  { return sessionStorage.getItem(_skey(k)) !== 'closed'; }
function _setOpen(k, open) { sessionStorage.setItem(_skey(k), open ? 'open' : 'closed'); }

/* ====== Nav tree renderers ====== */
function _nodeContainsPath(node, path) {
  if (!path) return false;
  if (node.url === path) return true;
  if (node.children) return node.children.some(c => _nodeContainsPath(c, path));
  return false;
}

function _renderLink(node, depth, currentPath) {
  const hasKids  = node.children && node.children.length > 0;
  const isActive = node.url === currentPath;
  const nodeKey  = 'n_' + node.url;
  const kidActive = !isActive && hasKids && node.children.some(c => _nodeContainsPath(c, currentPath));
  const open = hasKids && (isActive || kidActive);

  const wrap = document.createElement('div');
  wrap.className = 'nt-node';

  const row = document.createElement('div');
  row.className = 'nt-row' + (isActive ? ' nt-active' : '');
  row.style.paddingLeft = (14 + depth * 12) + 'px';

  if (hasKids) {
    const tog = document.createElement('button');
    tog.className = 'nt-toggle';
    tog.innerHTML = open ? ICON_DOWN : ICON_RIGHT;

    const lnk = document.createElement('a');
    lnk.className = 'nt-link';
    lnk.href = node.url;
    lnk.textContent = node.title;

    row.appendChild(tog);
    row.appendChild(lnk);
    wrap.appendChild(row);

    const kids = document.createElement('div');
    kids.className = 'nt-children';
    if (!open) kids.style.display = 'none';
    node.children.forEach(c => kids.appendChild(_renderLink(c, depth + 1, currentPath)));
    wrap.appendChild(kids);

    tog.addEventListener('click', e => {
      e.stopPropagation();
      const nowOpen = kids.style.display !== 'none';
      kids.style.display = nowOpen ? 'none' : '';
      tog.innerHTML = nowOpen ? ICON_RIGHT : ICON_DOWN;
      _setOpen(nodeKey, !nowOpen);
    });
  } else {
    const lnk = document.createElement('a');
    lnk.className = 'nt-link nt-leaf';
    lnk.href = node.url;
    lnk.textContent = node.title;
    row.appendChild(lnk);
    wrap.appendChild(row);
  }

  return wrap;
}

function _renderSection(section, sIdx, sourceId, currentPath) {
  const secKey = 'sec_' + sourceId + '_' + sIdx;
  // Auto-expand section if it contains the current page
  const hasCurrent = section.items.some(n => _nodeContainsPath(n, currentPath));
  const open = hasCurrent;

  const wrap = document.createElement('div');
  wrap.className = 'nt-section';

  const hdr = document.createElement('button');
  hdr.className = 'nt-section-hdr';
  hdr.innerHTML = (open ? ICON_DOWN : ICON_RIGHT) + '<span>' + section.title + '</span>';

  const body = document.createElement('div');
  body.className = 'nt-section-body';
  if (!open) body.style.display = 'none';
  section.items.forEach(node => body.appendChild(_renderLink(node, 0, currentPath)));

  hdr.addEventListener('click', () => {
    const nowOpen = body.style.display !== 'none';
    body.style.display = nowOpen ? 'none' : '';
    hdr.innerHTML = (nowOpen ? ICON_RIGHT : ICON_DOWN) + '<span>' + section.title + '</span>';
    _setOpen(secKey, !nowOpen);
  });

  wrap.appendChild(hdr);
  wrap.appendChild(body);
  return wrap;
}

function _renderNavTree(container, data, sourceId) {
  container.innerHTML = '';
  data.forEach((section, i) => {
    if (section.type === 'link') {
      const a = document.createElement('a');
      a.className = 'nt-link nt-nav-shortcut' + (section.url === _currentPath ? ' nt-active' : '');
      a.href = section.url;
      a.textContent = section.title;
      container.appendChild(a);
    } else {
      container.appendChild(_renderSection(section, i, sourceId, _currentPath));
    }
  });
}

/* ====== All-sources sidebar ====== */
async function buildAllSourcesNav() {
  const root = document.getElementById('all-sources-nav');
  if (!root) return;

  // Expand All / Collapse All buttons side by side
  const btnRow = document.createElement('div');
  btnRow.className = 'st-expand-row';

  const expandBtn = document.createElement('button');
  expandBtn.className = 'st-expand-all';
  expandBtn.textContent = 'Expand All';
  expandBtn.addEventListener('click', async () => {
    const treeSrcs = root.querySelectorAll('.st-wrap[data-tree]');
    for (const wrap of treeSrcs) {
      const tog  = wrap.querySelector(':scope > .st-toggle');
      const body = wrap.querySelector(':scope > .st-body');
      if (!tog || !body) continue;
      const srcId = wrap.dataset.tree;
      body.style.display = '';
      tog.innerHTML = ICON_DOWN + `<span class="st-icon">${tog.dataset.icon}</span><span class="st-label">${tog.dataset.label}</span>`;
      if (!_navCache[srcId]) {
        body.innerHTML = '<div class="nt-loading">Loading…</div>';
        try {
          const r = await fetch('/api/nav/' + srcId);
          _navCache[srcId] = await r.json();
          _renderNavTree(body, _navCache[srcId], srcId);
        } catch(e) { body.innerHTML = '<div class="nt-loading">Failed to load</div>'; }
      }
      _setOpen('src_' + srcId, true);
    }
  });

  const collapseBtn = document.createElement('button');
  collapseBtn.className = 'st-expand-all';
  collapseBtn.textContent = 'Collapse All';
  collapseBtn.addEventListener('click', () => {
    const treeSrcs = root.querySelectorAll('.st-wrap[data-tree]');
    treeSrcs.forEach(wrap => {
      const tog  = wrap.querySelector(':scope > .st-toggle');
      const body = wrap.querySelector(':scope > .st-body');
      if (!tog || !body) return;
      const srcId = wrap.dataset.tree;
      body.style.display = 'none';
      tog.innerHTML = ICON_RIGHT + `<span class="st-icon">${tog.dataset.icon}</span><span class="st-label">${tog.dataset.label}</span>`;
      _setOpen('src_' + srcId, false);
    });
  });

  btnRow.appendChild(expandBtn);
  btnRow.appendChild(collapseBtn);
  root.appendChild(btnRow);

  for (const src of SOURCES) {
    const srcKey = 'src_' + src.id;
    const isActive = src.id === _activeSource;

    const wrap = document.createElement('div');
    wrap.className = 'st-wrap';

    // Sources with noNav: just a link, no expandable tree
    if (src.noNav) {
      const lnk = document.createElement('a');
      lnk.className = 'st-toggle st-toggle-link' + (isActive ? ' st-toggle-active' : '');
      lnk.href = '/source/' + src.id;
      lnk.style.setProperty('--c', src.color);
      lnk.innerHTML = `<span class="st-icon">${src.icon}</span><span class="st-label">${src.label}</span>`;
      wrap.appendChild(lnk);
      root.appendChild(wrap);

      // Inject Compiled Binaries link immediately after LOLBAS
      if (src.id === 'lolbas') {
        const binWrap = document.createElement('div');
        binWrap.className = 'st-wrap';
        const isBinActive = window.location.pathname === '/binaries/' || window.location.pathname.startsWith('/binaries/');
        const binLnk = document.createElement('a');
        binLnk.className = 'st-toggle st-toggle-link' + (isBinActive ? ' st-toggle-active' : '');
        binLnk.href = '/binaries/';
        binLnk.style.setProperty('--c', '#2ac3de');
        binLnk.innerHTML = '<span class="st-icon">💾</span><span class="st-label">Compiled Binaries</span>';
        binWrap.appendChild(binLnk);
        root.appendChild(binWrap);
      }
      continue;
    }

    const open = isActive || sessionStorage.getItem(_skey(srcKey)) === 'open';

    wrap.dataset.tree = src.id;

    // Top-level source toggle button
    const tog = document.createElement('button');
    tog.className = 'st-toggle' + (isActive ? ' st-toggle-active' : '');
    tog.style.setProperty('--c', src.color);
    tog.dataset.icon  = src.icon;
    tog.dataset.label = src.label;
    tog.innerHTML = `${open ? ICON_DOWN : ICON_RIGHT}<span class="st-icon">${src.icon}</span><span class="st-label">${src.label}</span>`;

    const body = document.createElement('div');
    body.className = 'st-body';
    if (!open) body.style.display = 'none';

    let loaded = false;

    async function expand(s, b) {
      if (!loaded) {
        loaded = true;
        b.innerHTML = '<div class="nt-loading">Loading…</div>';
        try {
          if (!_navCache[s.id]) {
            const r = await fetch('/api/nav/' + s.id);
            _navCache[s.id] = await r.json();
          }
          _renderNavTree(b, _navCache[s.id], s.id);
          const activeRow = b.querySelector('.nt-active');
          if (activeRow) activeRow.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        } catch(e) {
          b.innerHTML = '<div class="nt-loading">Failed to load</div>';
        }
      }
    }

    if (open) expand(src, body);

    tog.addEventListener('click', async () => {
      const nowOpen = body.style.display !== 'none';
      if (!nowOpen) {
        body.style.display = '';
        tog.innerHTML = ICON_DOWN + `<span class="st-icon">${src.icon}</span><span class="st-label">${src.label}</span>`;
        await expand(src, body);
        _setOpen(srcKey, true);
      } else {
        body.style.display = 'none';
        tog.innerHTML = ICON_RIGHT + `<span class="st-icon">${src.icon}</span><span class="st-label">${src.label}</span>`;
        _setOpen(srcKey, false);
      }
    });

    wrap.appendChild(tog);
    wrap.appendChild(body);
    root.appendChild(wrap);
  }

  // Restore saved scroll position after tree is built
  const savedScroll = sessionStorage.getItem('pt_nav_scroll');
  if (savedScroll) root.scrollTop = parseInt(savedScroll, 10);

  // Persist scroll position across navigations
  root.addEventListener('scroll', () => {
    sessionStorage.setItem('pt_nav_scroll', root.scrollTop);
  }, { passive: true });
}

/* ====== Badge source filter toggles ====== */
// All sources on by default (empty set = all). A source in _offSources is excluded.
const _offSources = new Set();

function _initBadgeToggles() {
  document.querySelectorAll('.source-badge[data-source-id]').forEach(badge => {
    badge.addEventListener('click', e => {
      e.preventDefault();
      const sid = badge.dataset.sourceId;
      if (_offSources.has(sid)) {
        _offSources.delete(sid);
        badge.classList.remove('badge-off');
      } else {
        _offSources.add(sid);
        badge.classList.add('badge-off');
      }
      // Re-run search if active
      if (searchInput && searchInput.value.trim().length >= 2) {
        _runSearch(searchInput.value.trim());
      }
    });
  });
}

/* ====== Search ====== */
const searchInput = document.getElementById('search-input');
const searchDrop  = document.getElementById('search-dropdown');
let _index = null, _fuse = null, _activeIdx = -1;

async function loadIndex() {
  if (_index) return;
  try {
    const r = await fetch('/api/index');
    _index = await r.json();
    _fuse = new Fuse(_index, { keys: ['title','excerpt'], threshold: 0.35, minMatchCharLength: 2, includeScore: true });
  } catch(e) {}
}

function _filteredResults(fuseHits) {
  let items = fuseHits.map(h => h.item);
  if (_offSources.size > 0) {
    items = items.filter(r => !_offSources.has(r.source));
  }
  return items;
}

function renderDropdown(results) {
  if (!results.length) {
    searchDrop.innerHTML = '<div class="sd-empty">No results</div>';
    searchDrop.classList.add('open'); _activeIdx = -1; return;
  }
  searchDrop.innerHTML = results.slice(0, 12).map((r, i) => {
    const src = SOURCES.find(s => s.id === r.source) || {};
    return `<a class="sd-item" href="${r.url}">
      <div class="sd-source" style="color:${src.color||'#c0caf5'}">${src.icon||''} ${src.label||r.source}</div>
      <div class="sd-title">${r.title}</div>
      ${r.excerpt ? `<div class="sd-excerpt">${r.excerpt.slice(0,100)}</div>` : ''}
    </a>`;
  }).join('');
  searchDrop.classList.add('open'); _activeIdx = -1;
}

function closeDropdown() { searchDrop.classList.remove('open'); searchDrop.innerHTML = ''; _activeIdx = -1; }

async function _runSearch(q) {
  await loadIndex();
  if (_fuse) renderDropdown(_filteredResults(_fuse.search(q)));
}

if (searchInput) {
  searchInput.addEventListener('focus', loadIndex);
  searchInput.addEventListener('input', async () => {
    const q = searchInput.value.trim();
    if (q.length < 2) { closeDropdown(); return; }
    await _runSearch(q);
  });
  searchInput.addEventListener('keydown', e => {
    const items = searchDrop.querySelectorAll('.sd-item');
    if (e.key === 'ArrowDown') { e.preventDefault(); _activeIdx = Math.min(_activeIdx+1, items.length-1); items.forEach((el,i)=>el.classList.toggle('active',i===_activeIdx)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); _activeIdx = Math.max(_activeIdx-1,-1); items.forEach((el,i)=>el.classList.toggle('active',i===_activeIdx)); }
    else if (e.key === 'Enter') { if (_activeIdx>=0&&items[_activeIdx]) window.location=items[_activeIdx].href; else if (searchInput.value.trim()) window.location='/search?q='+encodeURIComponent(searchInput.value.trim()); }
    else if (e.key === 'Escape') { closeDropdown(); searchInput.blur(); }
  });
}
document.addEventListener('click', e => { if (!e.target.closest('.header-search')) closeDropdown(); });
document.addEventListener('keydown', e => {
  if ((e.ctrlKey||e.metaKey) && e.key==='k') { e.preventDefault(); if (searchInput) { searchInput.focus(); searchInput.select(); loadIndex(); } }
});

/* ====== Copy buttons ====== */
function addCopyButtons() {
  document.querySelectorAll('.page-body pre').forEach(pre => {
    if (pre.querySelector('.copy-btn')) return;
    const btn = document.createElement('button');
    btn.className = 'copy-btn'; btn.title = 'Copy'; btn.setAttribute('aria-label','Copy code');
    btn.innerHTML = ICON_COPY;
    btn.addEventListener('click', () => {
      const code = pre.querySelector('code');
      navigator.clipboard.writeText(code ? code.innerText : pre.innerText).then(() => {
        btn.classList.add('copied'); btn.innerHTML = ICON_CHECK;
        setTimeout(() => { btn.classList.remove('copied'); btn.innerHTML = ICON_COPY; }, 2000);
      });
    });
    pre.appendChild(btn);
  });
}

/* ====== Mobile sidebar ====== */
const mobileBtn = document.getElementById('mobile-menu-btn');
const sidebar   = document.getElementById('sidebar');
const overlay   = document.getElementById('sidebar-overlay');
if (mobileBtn && sidebar) {
  mobileBtn.addEventListener('click', () => { sidebar.classList.toggle('open'); overlay&&overlay.classList.toggle('open'); });
  overlay&&overlay.addEventListener('click', () => { sidebar.classList.remove('open'); overlay.classList.remove('open'); });
}

/* ====== Variable Substitution System ====== */
const VAR_META = {
  // Target
  'ip':               { label: 'Target IP',              placeholder: '10.10.10.1',           group: 'Target'      },
  'target':           { label: 'Target IP / Hostname',   placeholder: '10.10.10.1',           group: 'Target'      },
  'host':             { label: 'Target Host',            placeholder: '10.10.10.1',           group: 'Target'      },
  'hostname':         { label: 'Target Hostname',        placeholder: 'target.corp.local',    group: 'Target'      },
  'rhost':            { label: 'RHOST (Target IP)',      placeholder: '10.10.10.1',           group: 'Target'      },
  'target-ip':        { label: 'Target IP',              placeholder: '10.10.10.1',           group: 'Target'      },
  'victim-ip':        { label: 'Victim IP',              placeholder: '10.10.10.1',           group: 'Target'      },
  // Attacker
  'lhost':            { label: 'LHOST (Attacker IP)',    placeholder: '10.10.14.5',           group: 'Attacker'    },
  'lport':            { label: 'LPORT (Listener Port)',  placeholder: '4444',                 group: 'Attacker'    },
  'attacker-ip':      { label: 'Attacker IP',            placeholder: '10.10.14.5',           group: 'Attacker'    },
  'my-ip':            { label: 'Attacker IP',            placeholder: '10.10.14.5',           group: 'Attacker'    },
  // Network
  'port':             { label: 'Target Port',            placeholder: '445',                  group: 'Network'     },
  'rport':            { label: 'Target Port',            placeholder: '445',                  group: 'Network'     },
  'interface':        { label: 'Network Interface',      placeholder: 'eth0',                 group: 'Network'     },
  'protocol':         { label: 'Protocol',               placeholder: 'tcp',                  group: 'Network'     },
  // Active Directory
  'domain':           { label: 'Domain',                 placeholder: 'corp.local',           group: 'AD'          },
  'realm':            { label: 'Kerberos Realm',         placeholder: 'CORP.LOCAL',           group: 'AD'          },
  'fqdn':             { label: 'FQDN',                   placeholder: 'dc01.corp.local',      group: 'AD'          },
  'dc-ip':            { label: 'DC IP',                  placeholder: '10.10.10.1',           group: 'AD'          },
  'dc':               { label: 'Domain Controller',      placeholder: '10.10.10.1',           group: 'AD'          },
  'domain-controller':{ label: 'Domain Controller IP',   placeholder: '10.10.10.1',           group: 'AD'          },
  'ca':               { label: 'Certificate Authority',  placeholder: 'corp-CA',              group: 'AD'          },
  'template':         { label: 'Cert Template',          placeholder: 'User',                 group: 'AD'          },
  'upn':              { label: 'UPN',                    placeholder: 'user@corp.local',      group: 'AD'          },
  'spn':              { label: 'SPN',                    placeholder: 'cifs/dc01.corp.local', group: 'AD'          },
  'sid':              { label: 'SID',                    placeholder: 'S-1-5-21-...',         group: 'AD'          },
  // Credentials — authenticated (who you are)
  'username':         { label: 'Username (Auth)',        placeholder: 'administrator',        group: 'Auth User'   },
  'user':             { label: 'Username (Auth)',        placeholder: 'administrator',        group: 'Auth User'   },
  'u':                { label: 'Username (Auth)',        placeholder: 'administrator',        group: 'Auth User'   },
  'attacker-user':    { label: 'Attacker Username',     placeholder: 'attacker',             group: 'Auth User'   },
  'auth-user':        { label: 'Authenticated User',    placeholder: 'administrator',        group: 'Auth User'   },
  'password':         { label: 'Password',               placeholder: 'P@ssw0rd!',           group: 'Auth User'   },
  'pass':             { label: 'Password',               placeholder: 'P@ssw0rd!',           group: 'Auth User'   },
  'pwd':              { label: 'Password',               placeholder: 'P@ssw0rd!',           group: 'Auth User'   },
  // Credentials — target (who you're attacking)
  'target-user':      { label: 'Target Username',       placeholder: 'jsmith',               group: 'Target User' },
  'victim-user':      { label: 'Victim Username',       placeholder: 'jsmith',               group: 'Target User' },
  'target-username':  { label: 'Target Username',       placeholder: 'jsmith',               group: 'Target User' },
  // Hashes & keys
  'hash':             { label: 'NTLM Hash',              placeholder: 'aad3b435...:<NT>',     group: 'Hashes'      },
  'nt-hash':          { label: 'NT Hash',                placeholder: 'fc525c9dc....',        group: 'Hashes'      },
  'ntlm-hash':        { label: 'NTLM Hash',              placeholder: 'LM:NT',               group: 'Hashes'      },
  'lm-hash':          { label: 'LM Hash',                placeholder: 'aad3b435b514...',      group: 'Hashes'      },
  'rc4':              { label: 'RC4 / NTLM Key',         placeholder: 'fc525c9dc....',        group: 'Hashes'      },
  'rc4-key':          { label: 'RC4 Key',                placeholder: 'fc525c9dc....',        group: 'Hashes'      },
  'rc4password':      { label: 'RC4 Password',           placeholder: 'mysecret',             group: 'Hashes'      },
  'aes-key':          { label: 'AES-256 Key',            placeholder: 'b65e....',             group: 'Hashes'      },
  'aes128-key':       { label: 'AES-128 Key',            placeholder: '...',                  group: 'Hashes'      },
  'aes256-key':       { label: 'AES-256 Key',            placeholder: '...',                  group: 'Hashes'      },
  // Files & paths
  'pfx':              { label: 'PFX Certificate File',   placeholder: 'cert.pfx',             group: 'Files'       },
  'cert':             { label: 'Certificate File',       placeholder: 'cert.pem',             group: 'Files'       },
  'key':              { label: 'Key File',               placeholder: 'key.pem',              group: 'Files'       },
  'output':           { label: 'Output File',            placeholder: 'output.txt',           group: 'Files'       },
  'file':             { label: 'File Path',              placeholder: '/tmp/shell',           group: 'Files'       },
  'path':             { label: 'Path',                   placeholder: '/tmp/shell',           group: 'Files'       },
  'share':            { label: 'SMB Share',              placeholder: 'C$',                   group: 'Files'       },
  // Misc
  'name':             { label: 'Name',                   placeholder: 'myshell',              group: 'Misc'        },
  'computer':         { label: 'Computer Name',          placeholder: 'WORKSTATION01',        group: 'Misc'        },
  'computer-name':    { label: 'Computer Name',          placeholder: 'WORKSTATION01',        group: 'Misc'        },
  'payload':          { label: 'Payload',                placeholder: 'windows/x64/meterpreter/reverse_tcp', group: 'Misc' },
  'password2':        { label: 'Password (secondary)',   placeholder: 'P@ssw0rd2',            group: 'Misc'        },
  // AD Extended
  'new-password':     { label: 'New Password',           placeholder: 'NewP@ss123!',          group: 'Auth User'   },
  'admin-username':   { label: 'Admin Username',         placeholder: 'administrator',        group: 'Auth User'   },
  'local-admin':      { label: 'Local Admin Username',   placeholder: 'administrator',        group: 'Auth User'   },
  'attacker-user':    { label: 'Attacker Username',      placeholder: 'attacker',             group: 'Auth User'   },
  'attacker-computer':{ label: 'Attacker Computer',      placeholder: 'ATTACKER$',            group: 'AD'          },
  'ca-host':          { label: 'CA Hostname',            placeholder: 'ca01.corp.local',      group: 'AD'          },
  'ca-name':          { label: 'CA Display Name',        placeholder: 'corp-CA',              group: 'AD'          },
  'dc-host':          { label: 'DC Hostname',            placeholder: 'dc01.corp.local',      group: 'AD'          },
  'dc-hostname':      { label: 'DC Hostname',            placeholder: 'dc01.corp.local',      group: 'AD'          },
  'dc-fqdn':          { label: 'DC FQDN',                placeholder: 'dc01.corp.local',      group: 'AD'          },
  'dc-name':          { label: 'DC Name',                placeholder: 'DC01',                 group: 'AD'          },
  'domain-sid':       { label: 'Domain SID',             placeholder: 'S-1-5-21-...',         group: 'AD'          },
  'target-sid':       { label: 'Target SID',             placeholder: 'S-1-5-21-...-1105',   group: 'AD'          },
  'target-computer':  { label: 'Target Computer',        placeholder: 'WORKSTATION01',        group: 'AD'          },
  'target-group':     { label: 'Target Group',           placeholder: 'Domain Admins',        group: 'AD'          },
  'group-name':       { label: 'Group Name',             placeholder: 'Domain Admins',        group: 'AD'          },
  'gmsa-account':     { label: 'gMSA Account',           placeholder: 'svc_gmsa$',            group: 'AD'          },
  'gpo-name':         { label: 'GPO Name',               placeholder: 'Default Domain Policy',group: 'AD'          },
  'ccache':           { label: 'Kerberos ccache File',   placeholder: '/tmp/krb5cc_user',     group: 'AD'          },
  'ticket':           { label: 'Kerberos Ticket File',   placeholder: 'ticket.ccache',        group: 'AD'          },
  'extra-sids':       { label: 'Extra SIDs',             placeholder: 'S-1-5-21-...-519',     group: 'AD'          },
  'nameserver':       { label: 'Nameserver',             placeholder: '10.10.10.1',           group: 'AD'          },
  'laps-password':    { label: 'LAPS Password',          placeholder: 'Aa1!Bb2@Cc3#',        group: 'AD'          },
  // Hashes (Extended)
  'krbtgt-hash':      { label: 'krbtgt NTLM Hash',       placeholder: 'fc525c9dc....',        group: 'Hashes'      },
  'krbtgt-ntlm-hash': { label: 'krbtgt NTLM Hash',       placeholder: 'fc525c9dc....',        group: 'Hashes'      },
  'krbtgt-aes256':    { label: 'krbtgt AES256 Key',      placeholder: 'b65e....',             group: 'Hashes'      },
  'attacker-ntlm-hash':{ label: 'Attacker NTLM Hash',   placeholder: 'fc525c9dc....',        group: 'Hashes'      },
  'target-ntlm-hash': { label: 'Target NTLM Hash',       placeholder: 'fc525c9dc....',        group: 'Hashes'      },
  'laps-ntlm-hash':   { label: 'LAPS NTLM Hash',         placeholder: 'fc525c9dc....',        group: 'Hashes'      },
  'ntlm-hash':        { label: 'NTLM Hash',              placeholder: 'LM:NT',               group: 'Hashes'      },
  'trust-key-hash':   { label: 'Trust Key Hash',         placeholder: 'fc525c9dc....',        group: 'Hashes'      },
  // Azure
  'tenant-id':        { label: 'Azure Tenant ID',        placeholder: '12345678-...',         group: 'Azure'       },
  'subscription-id':  { label: 'Azure Subscription ID',  placeholder: 'xxxxxxxx-...',         group: 'Azure'       },
  'app-id':           { label: 'Azure App / SP ID',      placeholder: 'xxxxxxxx-...',         group: 'Azure'       },
  'object-id':        { label: 'Azure Object ID',        placeholder: 'xxxxxxxx-...',         group: 'Azure'       },
  'resource-group':   { label: 'Resource Group',         placeholder: 'my-rg',               group: 'Azure'       },
  'vault-name':       { label: 'Key Vault Name',         placeholder: 'corp-keyvault',        group: 'Azure'       },
  'secret-name':      { label: 'Key Vault Secret Name',  placeholder: 'db-password',         group: 'Azure'       },
  'vm-name':          { label: 'VM Name',                placeholder: 'corp-vm01',            group: 'Azure'       },
  'access-token':     { label: 'Access Token',           placeholder: 'eyJ0eXA...',          group: 'Azure'       },
  'refresh-token':    { label: 'Refresh Token',          placeholder: 'eyJ0eXA...',          group: 'Azure'       },
  'new-secret':       { label: 'New Secret Value',       placeholder: 'MySecret123!',        group: 'Azure'       },
};

// When a var has no value, check if a known alias has been set and suggest it
const VAR_SUGGEST = {
  'target': 'ip',   'rhost': 'ip',   'host': 'ip',   'target-ip': 'ip',   'victim-ip': 'ip',
  'attacker-ip': 'lhost',   'my-ip': 'lhost',
  'pass': 'password',   'pwd': 'password',
  'user': 'username',   'u': 'username',   'auth-user': 'username',
  'dc': 'dc-ip',   'domain-controller': 'dc-ip',
  'dc-host': 'fqdn',   'dc-hostname': 'fqdn',   'dc-fqdn': 'fqdn',
  'realm': 'domain',
  'nt-hash': 'hash',   'ntlm-hash': 'hash',   'lm-hash': 'hash',
  'krbtgt-ntlm-hash': 'krbtgt-hash',
  'attacker-ntlm-hash': 'hash',
  'ca-host': 'ca',   'ca-name': 'ca',
  'group-name': 'target-group',
  'local-admin': 'username',   'admin-username': 'username',
  'target-computer': 'computer',
  'attacker-computer': 'computer-name',
};

function _getVars()   { try { return JSON.parse(sessionStorage.getItem('pt_vars') || '{}'); } catch { return {}; } }
function _saveVars(v) { sessionStorage.setItem('pt_vars', JSON.stringify(v)); }
function _clearVars() { sessionStorage.removeItem('pt_vars'); }

/* ====== Distro toggle ====== */
// [exegol-canonical, kali, script]  — longer/more-specific names first
// [exegol, kali, script]
const DISTRO_TOOLS = [
  ['GetUserSPNs.py',          'impacket-GetUserSPNs',          'python3 GetUserSPNs.py'],
  ['GetNPUsers.py',            'impacket-GetNPUsers',           'python3 GetNPUsers.py'],
  ['GetLAPSPassword.py',       'impacket-GetLAPSPassword',      'python3 GetLAPSPassword.py'],
  ['GetADComputers.py',        'impacket-GetADComputers',       'python3 GetADComputers.py'],
  ['GetADUsers.py',            'impacket-GetADUsers',           'python3 GetADUsers.py'],
  ['CheckLDAPStatus.py',       'impacket-CheckLDAPStatus',      'python3 CheckLDAPStatus.py'],
  ['ticketConverter.py',       'impacket-ticketConverter',      'python3 ticketConverter.py'],
  ['describeTicket.py',        'impacket-describeTicket',       'python3 describeTicket.py'],
  ['machineAccountQuota.py',   'impacket-machineAccountQuota',  'python3 machineAccountQuota.py'],
  ['findDelegation.py',        'impacket-findDelegation',       'python3 findDelegation.py'],
  ['DumpNTLMInfo.py',          'impacket-DumpNTLMInfo',         'python3 DumpNTLMInfo.py'],
  ['changepasswd.py',          'impacket-changepasswd',         'python3 changepasswd.py'],
  ['addcomputer.py',           'impacket-addcomputer',          'python3 addcomputer.py'],
  ['ntlmrelayx.py',            'impacket-ntlmrelayx',           'python3 ntlmrelayx.py'],
  ['badsuccessor.py',          'impacket-badsuccessor',         'python3 badsuccessor.py'],
  ['mssqlclient.py',           'impacket-mssqlclient',          'python3 mssqlclient.py'],
  ['secretsdump.py',           'impacket-secretsdump',          'python3 secretsdump.py'],
  ['lookupsid.py',             'impacket-lookupsid',            'python3 lookupsid.py'],
  ['ldap_shell.py',            'impacket-ldap_shell',           'python3 ldap_shell.py'],
  ['dacledit.py',              'impacket-dacledit',             'python3 dacledit.py'],
  ['owneredit.py',             'impacket-owneredit',            'python3 owneredit.py'],
  ['samrdump.py',              'impacket-samrdump',             'python3 samrdump.py'],
  ['smbclient.py',             'impacket-smbclient',            'python3 smbclient.py'],
  ['smbserver.py',             'impacket-smbserver',            'python3 smbserver.py'],
  ['smbexec.py',               'impacket-smbexec',              'python3 smbexec.py'],
  ['wmiexec.py',               'impacket-wmiexec',              'python3 wmiexec.py'],
  ['dcomexec.py',              'impacket-dcomexec',             'python3 dcomexec.py'],
  ['atexec.py',                'impacket-atexec',               'python3 atexec.py'],
  ['psexec.py',                'impacket-psexec',               'python3 psexec.py'],
  ['ticketer.py',              'impacket-ticketer',             'python3 ticketer.py'],
  ['goldenPac.py',             'impacket-goldenPac',            'python3 goldenPac.py'],
  ['raiseChild.py',            'impacket-raiseChild',           'python3 raiseChild.py'],
  ['regsecrets.py',            'impacket-regsecrets',           'python3 regsecrets.py'],
  ['tgssub.py',                'impacket-tgssub',               'python3 tgssub.py'],
  ['getTGT.py',                'impacket-getTGT',               'python3 getTGT.py'],
  ['getST.py',                 'impacket-getST',                'python3 getST.py'],
  ['rpcdump.py',               'impacket-rpcdump',              'python3 rpcdump.py'],
  ['dpapi.py',                 'impacket-dpapi',                'python3 dpapi.py'],
  ['rbcd.py',                  'impacket-rbcd',                 'python3 rbcd.py'],
  ['reg.py',                   'impacket-reg',                  'python3 reg.py'],
  ['services.py',              'impacket-services',             'python3 services.py'],
  // Certipy
  ['certipy ',                 'certipy-ad ',                   'certipy-ad '],
  ['certipy\n',                'certipy-ad\n',                  'certipy-ad\n'],
  // BloodyAD
  ['python bloodyAD.py',       'bloodyad',                      'python3 bloodyAD.py'],
  ['python3 bloodyAD.py',      'bloodyad',                      'python3 bloodyAD.py'],
  ['bloodyAD.py',              'bloodyad',                      'python3 bloodyAD.py'],
];

function _getDistro()  { return sessionStorage.getItem('pt_distro') || 'exegol'; }
function _setDistro(d) { sessionStorage.setItem('pt_distro', d); }
function _getImpl()    { return sessionStorage.getItem('pt_impl') || 'impacket'; }
function _setImpl(v)   { sessionStorage.setItem('pt_impl', v); }

function _applyDistroToHtml(html, mode) {
  if (mode === 'exegol') return html;
  DISTRO_TOOLS.forEach(([exegol, kali, script]) => {
    const replacement = mode === 'kali' ? kali : script;
    if (replacement !== exegol) html = html.split(exegol).join(replacement);
  });
  return html;
}

// When GoPacket impl is active, convert exegol canonical names → gopacket- directly,
// ignoring distro so gopacket-secretsdump always shows regardless of Kali/Exegol/Script.
function _applyGopacketToHtml(html) {
  DISTRO_TOOLS.forEach(([exegol, kali]) => {
    // Derive gopacket name from kali name (impacket-X → gopacket-X)
    const gopacket = kali.startsWith('impacket-') ? kali.replace('impacket-', 'gopacket-') : null;
    if (!gopacket) return;
    // Replace all three forms: exegol (.py), kali (impacket-), script (python3 .py)
    const script = 'python3 ' + exegol;
    html = html.split(script).join(gopacket);   // python3 secretsdump.py → gopacket-secretsdump
    html = html.split(exegol).join(gopacket);   // secretsdump.py → gopacket-secretsdump
    html = html.split(kali).join(gopacket);     // impacket-secretsdump → gopacket-secretsdump
  });
  return html;
}

// Unified render: distro/impl → vars → display
function _renderCode() {
  const mode = _getDistro();
  const impl = _getImpl();
  const vars = _getVars();
  document.querySelectorAll('.page-body pre code').forEach(el => {
    const pre = el.closest('pre');
    if (!pre.dataset.origHtml) pre.dataset.origHtml = el.innerHTML;
    // GoPacket impl always overrides distro — always shows gopacket- prefix
    let html = impl === 'gopacket'
      ? _applyGopacketToHtml(pre.dataset.origHtml)
      : _applyDistroToHtml(pre.dataset.origHtml, mode);
    Object.entries(vars).forEach(([k, v]) => {
      if (!v) return;
      const safe = v.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      html = html.split(`&lt;${k}&gt;`).join(`<span class="var-filled" title="&lt;${k}&gt;">${safe}</span>`);
    });
    el.innerHTML = html;
  });
}

function _applyImplNav(impl) {
  const root = document.getElementById('all-sources-nav');
  if (!root) return;
  root.querySelectorAll('.st-wrap').forEach(wrap => {
    const id = wrap.dataset.tree;
    if (id === 'impacket') wrap.style.display = impl === 'gopacket' ? 'none' : '';
    if (id === 'gopacket') wrap.style.display = impl === 'gopacket' ? ''     : 'none';
  });
}

function _initDistroToggle() {
  const saved = _getDistro();
  document.querySelectorAll('#distro-toggle .distro-btn').forEach(btn => {
    btn.classList.toggle('distro-btn-active', btn.dataset.distro === saved);
    btn.addEventListener('click', () => {
      const d = btn.dataset.distro;
      _setDistro(d);
      document.querySelectorAll('#distro-toggle .distro-btn').forEach(b =>
        b.classList.toggle('distro-btn-active', b.dataset.distro === d));
      _renderCode();
    });
  });
}

function _initImplToggle() {
  const saved = _getImpl();
  document.querySelectorAll('#impl-toggle .distro-btn').forEach(btn => {
    btn.classList.toggle('distro-btn-active', btn.dataset.impl === saved);
    btn.addEventListener('click', () => {
      const v = btn.dataset.impl;
      _setImpl(v);
      document.querySelectorAll('#impl-toggle .distro-btn').forEach(b =>
        b.classList.toggle('distro-btn-active', b.dataset.impl === v));
      _applyImplNav(v);
      _renderCode();
    });
  });
  _applyImplNav(saved);
}

// Scan code blocks for <varname> tokens — returns sorted unique list
function _detectPageVars() {
  const found = new Set();
  // Regex: <name> where name starts with a letter, contains letters/digits/hyphens/underscores/colons
  const re = /<([a-zA-Z][a-zA-Z0-9_:.-]*)>/g;
  document.querySelectorAll('.page-body pre code').forEach(el => {
    let m;
    while ((m = re.exec(el.textContent)) !== null) {
      found.add(m[1].toLowerCase());
    }
  });
  return [...found].sort();
}

// Substitute known vars into code blocks — delegates to _renderCode for distro+var chaining
function _applyVars(vars) {
  if (!Object.keys(vars).length) return;
  _renderCode();
}

function _restoreCode() {
  document.querySelectorAll('.page-body pre[data-orig-html]').forEach(pre => {
    const code = pre.querySelector('code');
    if (code) {
      // Restore to distro-applied state (not fully original), so distro stays active
      const base = _applyDistroToHtml(pre.dataset.origHtml, _getDistro());
      code.innerHTML = base;
    }
  });
}

function _updateVarBadge() {
  const badge = document.getElementById('var-badge');
  if (!badge) return;
  const n = Object.values(_getVars()).filter(v => v).length;
  badge.textContent = n || '';
  badge.classList.toggle('var-badge-active', n > 0);
}

function _getSuggestion(varName, session) {
  const canon = VAR_SUGGEST[varName];
  return canon ? (session[canon] || '') : '';
}

function _openVarModal(showAll) {
  const modal   = document.getElementById('var-modal');
  const form    = document.getElementById('var-form');
  const title   = document.getElementById('var-modal-title-text');
  const hint    = document.getElementById('var-modal-hint');
  if (!modal || !form) return;

  const session = _getVars();
  form.innerHTML = '';

  if (showAll) {
    if (title) title.textContent = 'Edit Session Variables';
    if (hint)  hint.textContent  = 'All variables currently set in this session. Clear a field to unset it.';
  } else {
    if (title) title.textContent = 'Set Variables';
    if (hint)  hint.textContent  = 'Values apply to all code blocks on this page and persist across pages in this session.';
  }

  const varKeys = showAll
    ? Object.keys(session).filter(k => session[k])
    : _detectPageVars();

  if (!varKeys.length) {
    form.innerHTML = showAll
      ? '<p class="var-empty">No variables are currently set. Click <strong>Variables</strong> on a page to set them.</p>'
      : '<p class="var-empty">No <code>&lt;variable&gt;</code> placeholders found on this page.</p>';
  } else {
    const grouped = {};
    varKeys.forEach(v => {
      const meta  = VAR_META[v] || { label: v, placeholder: v, group: 'Other' };
      const group = meta.group || 'Other';
      (grouped[group] = grouped[group] || []).push({ v, meta });
    });

    const ORDER = ['Target','Attacker','Network','AD','Auth User','Target User','Hashes','Files','Misc','Other'];
    const groupKeys = [...ORDER.filter(g => grouped[g]), ...Object.keys(grouped).filter(g => !ORDER.includes(g))];

    groupKeys.forEach(group => {
      const sec = document.createElement('div');
      sec.className = 'var-group-block';
      sec.innerHTML = `<div class="var-group-label">${group}</div>`;

      grouped[group].forEach(({ v, meta }) => {
        const existing   = session[v] || '';
        const suggestion = !existing && !showAll ? _getSuggestion(v, session) : '';
        const displayVal = existing || suggestion;
        const row = document.createElement('div');
        row.className = 'var-row';
        row.innerHTML = `
          <label class="var-label" for="vf-${v}">
            <code class="var-token">&lt;${v}&gt;</code>
            <span class="var-label-text">${meta.label || v}</span>
          </label>
          <input class="var-input${suggestion && !existing ? ' var-suggested' : ''}"
                 id="vf-${v}" name="${v}" type="text"
                 value="${displayVal.replace(/"/g,'&quot;')}"
                 placeholder="${(meta.placeholder || v).replace(/"/g,'&quot;')}"
                 autocomplete="off" spellcheck="false">`;
        sec.appendChild(row);
      });

      form.appendChild(sec);
    });
  }

  modal.classList.add('open');
  const firstEmpty = form.querySelector('.var-input:not([value])') || form.querySelector('.var-input');
  if (firstEmpty) { firstEmpty.focus(); firstEmpty.select(); }
}

function _closeVarModal() {
  const modal = document.getElementById('var-modal');
  if (modal) modal.classList.remove('open');
}

function _submitVars() {
  const vars = _getVars();
  document.querySelectorAll('#var-form .var-input').forEach(inp => {
    const val = inp.value.trim();
    if (val) vars[inp.name] = val;
    else     delete vars[inp.name];
  });
  _saveVars(vars);
  _restoreCode();
  _applyVars(vars);
  _closeVarModal();
  _updateVarBadge();
}

function _initVarSystem() {
  // Apply distro transform + session vars on page load
  _renderCode();
  _updateVarBadge();

  const openBtn  = document.getElementById('var-open-btn');
  const clearBtn = document.getElementById('var-clear-btn');
  const modal    = document.getElementById('var-modal');
  const submitBtn= document.getElementById('var-submit');
  const cancelBtn= document.getElementById('var-cancel');

  if (openBtn)    openBtn.addEventListener('click', () => _openVarModal(false));
  const editAllBtn = document.getElementById('var-edit-all-btn');
  if (editAllBtn) editAllBtn.addEventListener('click', () => _openVarModal(true));
  if (clearBtn) clearBtn.addEventListener('click', () => { _clearVars(); _restoreCode(); _updateVarBadge(); });
  if (submitBtn) submitBtn.addEventListener('click', _submitVars);
  if (cancelBtn) cancelBtn.addEventListener('click', _closeVarModal);

  if (modal) {
    // Close on backdrop click
    modal.addEventListener('click', e => { if (e.target === modal) _closeVarModal(); });
    // Submit on Enter, close on Escape
    modal.addEventListener('keydown', e => {
      if (e.key === 'Escape') _closeVarModal();
      if (e.key === 'Enter' && e.target.classList.contains('var-input')) { e.preventDefault(); _submitVars(); }
    });
  }
}

/* ====== Init ====== */
function _initSearchHelp() {
  const btn     = document.getElementById('search-help-btn');
  const overlay = document.getElementById('search-help-overlay');
  const close   = document.getElementById('search-help-close');
  if (!btn || !overlay) return;
  const open  = () => overlay.classList.add('open');
  const close_ = () => overlay.classList.remove('open');
  btn.addEventListener('click', open);
  close && close.addEventListener('click', close_);
  overlay.addEventListener('click', e => { if (e.target === overlay) close_(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close_(); });
}

/* ====== Offline badge injection ====== */
function _initOfflineBadges() {
  // Config is injected server-side as window.__OFFLINE__ — no async fetch needed.
  const cfg = window.__OFFLINE__;
  if (!cfg || !cfg.offline) return;

  const toolMap   = cfg.tool_map  || {};
  const available = cfg.tools     || {};

  // Build lookup: lowercased slug → local tool dir name
  const slugToDir = {};
  for (const [slug, dir] of Object.entries(toolMap)) {
    slugToDir[slug.toLowerCase()] = dir;
  }

  function _resolveGithubHref(href) {
    if (!href.includes('github.com')) return null;
    const m = href.match(/github\.com\/([^/#?]+\/[^/#?\s"]+)/i);
    if (!m) return null;
    const slug = m[1].toLowerCase().replace(/\.git$/, '');
    const dir  = slugToDir[slug];
    if (!dir) return null;
    return { dir, local: !!available[dir] };
  }

  function _applyBadge(a) {
    if (a.dataset.offlineDone) return;
    a.dataset.offlineDone = '1';
    const res = _resolveGithubHref(a.getAttribute('href') || '');
    if (!res) return;

    if (res.local) {
      a.href  = `/tools/${res.dir}/`;
      a.title = `Local copy: ${res.dir}`;
      a.style.color = 'var(--green)';
      const badge = document.createElement('span');
      badge.className = 'offline-badge';
      badge.textContent = '📥';
      badge.style.cssText = 'margin-left:3px;font-size:.8rem;';
      a.appendChild(badge);
    } else {
      a.target = '_blank';
      a.rel    = 'noopener';
      const badge = document.createElement('span');
      badge.className = 'offline-badge';
      badge.textContent = '⬇';
      badge.title = `Not downloaded: ${res.dir}`;
      badge.style.cssText = 'margin-left:3px;font-size:.8rem;color:var(--orange);';
      a.appendChild(badge);
    }
  }

  // Scan page-body on load
  const body = document.querySelector('.page-body');
  if (body) body.querySelectorAll('a[href]').forEach(_applyBadge);

  // Also intercept clicks anywhere on the page as a safety net
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href]');
    if (!a || a.dataset.offlineDone) return;
    const res = _resolveGithubHref(a.getAttribute('href') || '');
    if (!res || !res.local) return;
    e.preventDefault();
    window.location.href = `/tools/${res.dir}/`;
  }, true);
}

document.addEventListener('DOMContentLoaded', () => {
  addCopyButtons();
  buildAllSourcesNav();
  _initBadgeToggles();
  _initDistroToggle();
  _initImplToggle();
  _initVarSystem();
  _initSearchHelp();
  _initOfflineBadges();
});
