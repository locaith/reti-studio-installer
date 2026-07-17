/* RETI Studio — luồng "Tạo TVC chuyên nghiệp" v2.
   Vào workspace → duyệt Drive theo ngăn → chọn ảnh → 1 nút → dựng. */
(function () {
  "use strict";
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };

  var STYLES = [
    { k:'cinematic',  t:'Điện ảnh',   sw:'linear-gradient(135deg,#123,#1a3a4a 50%,#c86a3a)' },
    { k:'luxury',     t:'Sang trọng', sw:'linear-gradient(135deg,#3a2a10,#8a6a2a 60%,#e0b060)' },
    { k:'modern',     t:'Hiện đại',   sw:'linear-gradient(135deg,#123a4a,#2a6a7a 60%,#a0d0d8)' },
    { k:'warm',       t:'Ấm áp',      sw:'linear-gradient(135deg,#4a1a10,#a04a20 60%,#f0a050)' },
    { k:'minimal',    t:'Tối giản',   sw:'linear-gradient(135deg,#33383f,#6a7078 60%,#c8ccd0)' },
    { k:'vibrant',    t:'Năng động',  sw:'linear-gradient(135deg,#5a1040,#c02060 55%,#ff8040)' },
    { k:'night',      t:'Đêm / Neon', sw:'linear-gradient(135deg,#10102a,#3a2060 55%,#8040c0)' },
    { k:'documentary',t:'Tài liệu',   sw:'linear-gradient(135deg,#2a3020,#4a5a30 60%,#90a060)' }
  ];
  var FONTS = [
    { t:'Thanh lịch',  ff:"Georgia,'Times New Roman',serif", it:'italic', w:'500', up:0, ls:'0' },
    { t:'Hiện đại đậm',ff:"system-ui,'Segoe UI',Roboto,sans-serif", it:'normal', w:'800', up:1, ls:'.01em' },
    { t:'Viết tay',    ff:"'Snell Roundhand','Segoe Script','Brush Script MT',cursive", it:'italic', w:'500', up:0, ls:'0' },
    { t:'Cổ điển',     ff:"'Times New Roman',Georgia,serif", it:'normal', w:'600', up:0, ls:'.01em' },
    { t:'Mạnh mẽ',     ff:"'Arial Narrow','Roboto Condensed',system-ui,sans-serif", it:'normal', w:'900', up:1, ls:'.02em' },
    { t:'Tối giản',    ff:"system-ui,'Segoe UI',sans-serif", it:'normal', w:'300', up:1, ls:'.16em' }
  ];
  var S = {
    link:'', folderId:'', images:[], bins:[], sel:{}, selCount:0, curBin:'all',
    style:0, font:1, aspect:'16:9', dur:45, quality:'standard', tvcStyle:'luxury_showcase', subs:'on',
    musicUrl:'', musicDownload:'', musicName:'', musicAttr:'',
    pid:null, tid:null, script:null
  };

  function esc(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]; }); }
  function thumbUrl(id) { return 'https://drive.google.com/thumbnail?id=' + id + '&sz=w400'; }
  function form(obj) { var fd = new FormData(); for (var k in obj) fd.append(k, obj[k]); return fd; }
  function post(url, obj) { return fetch(url, { method: 'POST', body: obj instanceof FormData ? obj : form(obj || {}) }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, code: r.status, data: d }; }).catch(function () { return { ok: r.ok, code: r.status, data: {} }; }); }); }
  function folderId(link) { var m = String(link).match(/[-\w]{25,}/); return m ? m[0] : ''; }
  function pool(items, worker, conc, onprog) {
    return new Promise(function (resolve) {
      var i = 0, done = 0, active = 0, n = items.length; if (!n) return resolve();
      function next() {
        while (active < conc && i < n) {
          (function (it) { active++; Promise.resolve(worker(it)).catch(function(){}).then(function () { active--; done++; if (onprog) onprog(done, n); if (done === n) resolve(); else next(); }); })(items[i++]);
        }
      }
      next();
    });
  }
  function one(cont, el) { cont.querySelectorAll('.pcard,.chip,.ms').forEach(function (x) { x.classList.remove('sel'); }); el.classList.add('sel'); }
  function setStep(n) { $$('.ptv-steps .ps').forEach(function (el) { el.classList.toggle('on', +el.dataset.s <= n); }); }

  /* ---------- style + font mini cards ---------- */
  var sc = $('#styles');
  STYLES.forEach(function (s, i) {
    var el = document.createElement('div'); el.className = 'pcard' + (i === 0 ? ' sel' : '');
    el.innerHTML = '<div class="sw" style="background:' + s.sw + '"></div><div class="t">' + s.t + '</div>';
    el.onclick = function () { one(sc, el); S.style = i; };
    sc.appendChild(el);
  });
  var fc = $('#fonts');
  FONTS.forEach(function (f, i) {
    var el = document.createElement('div'); el.className = 'pcard' + (i === 1 ? ' sel' : '');
    var tx = f.up ? 'THE PARKLAND' : 'The Parkland';
    el.innerHTML = '<div class="fp" style="font-family:' + f.ff + ';font-style:' + f.it + ';font-weight:' + f.w + ';letter-spacing:' + f.ls + ';text-transform:' + (f.up ? 'uppercase' : 'none') + '">' + tx + '</div><div class="t">' + f.t + '</div>';
    el.onclick = function () { one(fc, el); S.font = i; };
    fc.appendChild(el);
  });
  // TVC playbook: which of the two reference films this project should become.
  $$('#tvcstyle .pcard').forEach(function (c) {
    c.onclick = function () { one($('#tvcstyle'), c); S.tvcStyle = c.dataset.k; };
  });
  $$('#aspect .ms').forEach(function (c) { c.onclick = function () { one($('#aspect'), c); S.aspect = c.dataset.a; }; });
  $$('#dur .ms').forEach(function (c) { c.onclick = function () { one($('#dur'), c); S.dur = +c.dataset.d; }; });
  $$('#quality .ms').forEach(function (c) { c.onclick = function () { one($('#quality'), c); S.quality = c.dataset.q; }; });
  $$('#subs .ms').forEach(function (c) { c.onclick = function () { one($('#subs'), c); S.subs = c.dataset.s; }; });

  /* ---------- music picker modal ---------- */
  var mModal = $('#music-modal'), mList = $('#music-list'), mQ = $('#music-q');
  var mAudio = new Audio(); mAudio.preload = 'none'; var mNowRow = null, mNowBtn = null;
  var mMood = 'epic', mTimer = null;
  $('#music-pick').onclick = function () { mModal.hidden = false; if (!mList.querySelector('.trk')) loadMusic(); };
  $('#music-close').onclick = function () { stopPrev(); mModal.hidden = true; };
  $('#music-ai').onclick = function () {
    S.musicUrl = ''; S.musicDownload = ''; S.musicName = ''; S.musicAttr = '';
    $('#mp-name').textContent = 'AI tự tạo nhạc theo phong cách';
    $('#mp-sub').textContent = 'Nhấn để chọn từ kho nhạc'; $('#mp-ico').innerHTML = '♪';
    stopPrev(); mModal.hidden = true;
  };
  $$('#music-moods .chip').forEach(function (c) {
    c.onclick = function () { $('#music-moods').querySelectorAll('.chip').forEach(function (x){x.classList.remove('sel');}); c.classList.add('sel'); mMood = c.dataset.m; loadMusic(); };
  });
  mQ.oninput = function () { clearTimeout(mTimer); mTimer = setTimeout(loadMusic, 400); };
  function stopPrev() { mAudio.pause(); if (mNowRow) mNowRow.classList.remove('playing'); if (mNowBtn) mNowBtn.textContent = '▶'; mNowRow = null; mNowBtn = null; }
  function loadMusic() {
    stopPrev(); mList.innerHTML = '<div class="music-empty">Đang tải kho nhạc…</div>';
    var url = '/music/search?mood=' + encodeURIComponent(mMood) + '&q=' + encodeURIComponent(mQ.value.trim()) + '&limit=30';
    fetch(url).then(function (r) { return r.json(); }).then(function (d) {
      var tracks = (d && d.tracks) || [];
      if (!tracks.length) { mList.innerHTML = '<div class="music-empty">Không thấy bài phù hợp. Thử mood/từ khoá khác.</div>'; return; }
      mList.innerHTML = '';
      tracks.forEach(function (t) {
        var row = document.createElement('div'); row.className = 'trk';
        var dur = t.duration ? Math.floor(t.duration / 60) + ':' + ('0' + (t.duration % 60)).slice(-2) : '';
        row.innerHTML = (t.image ? '<img class="cover" src="' + esc(t.image) + '" loading="lazy" alt="">' : '<div class="cover"></div>')
          + '<button class="tplay" type="button">▶</button>'
          + '<div class="tmeta"><div class="tn">' + esc(t.name) + '</div><div class="ta">' + esc(t.artist) + '</div></div>'
          + '<div class="tdur">' + dur + '</div>';
        var btn = row.querySelector('.tplay');
        btn.onclick = function (e) {
          e.stopPropagation();
          if (mNowRow === row) { stopPrev(); return; }
          stopPrev(); mAudio.src = t.audio; mAudio.play().catch(function () {});
          row.classList.add('playing'); btn.textContent = '⏸'; mNowRow = row; mNowBtn = btn;
        };
        row.onclick = function () { selectTrack(t, row); };
        mList.appendChild(row);
      });
    }).catch(function () { mList.innerHTML = '<div class="music-empty">Lỗi tải kho nhạc.</div>'; });
  }
  function selectTrack(t, row) {
    mList.querySelectorAll('.trk').forEach(function (x) { x.classList.remove('sel'); });
    row.classList.add('sel');
    S.musicUrl = t.audio; S.musicDownload = t.download || t.audio; S.musicName = t.name; S.musicAttr = t.attribution || '';
    $('#mp-name').textContent = t.name; $('#mp-sub').textContent = t.artist || 'Đã chọn từ kho nhạc';
    $('#mp-ico').innerHTML = t.image ? '<img src="' + esc(t.image) + '" alt="">' : '♪';
    stopPrev(); mModal.hidden = true;
  }

  /* ---------- STEP 1: browse Drive ---------- */
  var browsing = false;
  $('#btn-browse').onclick = function () {
    if (browsing) return;
    var link = ($('#drive-link').value || '').trim();
    var fid = folderId(link);
    if (!fid) { alert('Link Drive chưa đúng. Dán link thư mục Google Drive (…/folders/…).'); return; }
    browsing = true; S.link = link; S.folderId = fid;
    var btn = this; btn.disabled = true;
    $('#browse-hint').hidden = true;
    var busy = $('#browse-busy'); busy.hidden = false; $('#browse-msg').textContent = 'Đang đọc thư mục Drive…';
    post('/drive/browse', { folder_id: fid }).then(function (r) {
      browsing = false; btn.disabled = false; busy.hidden = true;
      if (!r.ok) { $('#browse-hint').hidden = false; alert((r.data && r.data.detail) || 'Không đọc được thư mục Drive.'); return; }
      var imgs = (r.data && r.data.images) || [];
      if (!imgs.length) { $('#browse-hint').hidden = false; alert('Thư mục không có ảnh (hoặc chưa mở quyền "Bất kỳ ai có link").'); return; }
      S.images = imgs; S.bins = (r.data && r.data.bins) || [];
      autoSelect();  // AI gợi ý sẵn một subset đa dạng cho phim (không tick hết)
      renderBins(); selectBin('all');
      $('#workspace').hidden = false; $('#actionbar').hidden = false;
      updateSel(); setStep(2);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }).catch(function (e) {
      browsing = false; btn.disabled = false; busy.hidden = true; $('#browse-hint').hidden = false;
      alert('Lỗi: ' + (e.message || e));
    });
  };

  function renderBins() {
    var box = $('#bins'); box.innerHTML = '';
    box.appendChild(mkBin('all', 'Tất cả', S.images.length));
    S.bins.forEach(function (b) { box.appendChild(mkBin(b.name, b.name, b.count)); });
  }
  function mkBin(key, label, count) {
    var el = document.createElement('button'); el.type = 'button';
    el.className = 'pbin' + (key === S.curBin ? ' on' : ''); el.dataset.bin = key;
    el.innerHTML = '<span class="bi">' + esc((label || '?').slice(0, 1).toUpperCase()) + '</span>'
      + '<span class="bn">' + esc(label) + '</span><span class="bc">' + count + '</span>';
    el.onclick = function () { selectBin(key, label); };
    return el;
  }
  function selectBin(key, label) {
    S.curBin = key;
    $$('.pbin').forEach(function (x) { x.classList.toggle('on', x.dataset.bin === key); });
    var t = $('#grid-title'); if (t && t.firstChild) t.firstChild.textContent = (key === 'all' ? 'Tất cả nguyên liệu' : (label || key)) + ' ';
    renderGrid(key);
  }
  function renderGrid(bin) {
    var grid = $('#grid'); grid.innerHTML = '';
    var list = S.images.filter(function (im) { return bin === 'all' || im.bin === bin; });
    if (!list.length) { grid.innerHTML = '<div class="ptv-empty">Ngăn này chưa có ảnh.</div>'; return; }
    list.forEach(function (im) {
      var el = document.createElement('div'); el.className = 'ptile' + (S.sel[im.id] ? ' sel' : '');
      el.innerHTML = '<img src="' + thumbUrl(im.id) + '" loading="lazy" alt="" referrerpolicy="no-referrer">'
        + '<span class="ck"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg></span>'
        + '<span class="fn">' + esc(im.name || '') + '</span>';
      var img = el.querySelector('img');
      img.onerror = function () { el.classList.add('noimg'); img.remove(); };
      el.onclick = function () {
        if (S.sel[im.id]) { delete S.sel[im.id]; } else { S.sel[im.id] = true; }
        el.classList.toggle('sel'); updateSel();
      };
      grid.appendChild(el);
    });
  }
  function autoSelect() {
    // AI gợi ý: chọn sẵn một subset ĐA DẠNG (rải đều các ngăn) đủ cho thời lượng phim —
    // không tick hết; người dùng chỉ đổi ảnh nào không ưng. ~1 ảnh cho mỗi ~2.5s phim.
    S.sel = {};
    var target = Math.max(8, Math.min(14, Math.round(S.dur / 2.5)));
    if (target > S.images.length) target = S.images.length;
    var byBin = {}, order = [];
    S.images.forEach(function (im) { if (!byBin[im.bin]) { byBin[im.bin] = []; order.push(im.bin); } byBin[im.bin].push(im); });
    var picked = 0, idx = 0, guard = 0;
    while (picked < target && guard < 500) {
      var any = false;
      for (var b = 0; b < order.length && picked < target; b++) {
        var arr = byBin[order[b]];
        if (arr && arr[idx]) { S.sel[arr[idx].id] = true; picked++; any = true; }
      }
      idx++; guard++;
      if (!any) break;
    }
  }
  $('#pick-all').onclick = function () { pickAll(true); };
  $('#pick-none').onclick = function () { pickAll(false); };
  var reAuto = $('#pick-auto'); if (reAuto) reAuto.onclick = function () { autoSelect(); renderGrid(S.curBin); updateSel(); };
  function pickAll(v) {
    S.images.forEach(function (im) {
      if (S.curBin === 'all' || im.bin === S.curBin) { if (v) S.sel[im.id] = true; else delete S.sel[im.id]; }
    });
    renderGrid(S.curBin); updateSel();
  }
  function updateSel() {
    var n = 0; for (var k in S.sel) if (S.sel[k]) n++; S.selCount = n;
    var name = ($('#f-name').value || '').trim();
    if (n > 0) {
      $('#sel-count').textContent = 'Đã chọn ' + n + ' ảnh';
      $('#sel-sub').textContent = n >= 6 ? 'Đủ nguyên liệu — AI tự dựng nhịp phim'
        : 'Nên chọn thêm ~' + (6 - n) + ' ảnh';
    } else if (name) {
      // No Drive, no photos — still a supported case: the director agent researches the
      // project from its name and generates every shot with Veo.
      $('#sel-count').textContent = 'Chưa có ảnh — AI tự dựng';
      $('#sel-sub').textContent = 'AI nghiên cứu "' + name + '" và tạo toàn bộ cảnh';
    } else {
      $('#sel-count').textContent = 'Chưa có nguyên liệu';
      $('#sel-sub').textContent = 'Dán link Drive, hoặc chỉ cần điền Tên dự án';
    }
    $('#btn-create').disabled = (n === 0 && !name);
  }
  // The project name alone can start a film → re-evaluate the button as it's typed.
  $('#f-name').addEventListener('input', updateSel);

  /* ---------- STEP 2: create + import selected + script ---------- */
  function gs(k) { return document.querySelector('.gs[data-k="' + k + '"]'); }
  function genStep(k, cls) { var el = gs(k); if (el) { el.classList.remove('act', 'done'); if (cls) el.classList.add(cls); } }
  function genMsg(k, txt) { var el = gs(k); if (el) el.querySelector('b').textContent = txt; }

  var creating = false;
  $('#btn-create').onclick = function () {
    if (creating) return;
    var ids = []; for (var k in S.sel) if (S.sel[k]) ids.push(k);
    if (!ids.length && !($('#f-name').value || '').trim()) {
      alert('Hãy dán link Drive để chọn ảnh, HOẶC điền Tên dự án để AI tự dựng toàn bộ cảnh.');
      return;
    }
    creating = true;
    var ov = $('#gen-overlay'); ov.hidden = false;
    genStep('import', 'act'); genStep('analyze', ''); genStep('script', '');
    genMsg('import', '0/' + ids.length); genMsg('analyze', ''); genMsg('script', '');
    setStep(3);

    var byId = {}; S.images.forEach(function (im) { byId[im.id] = im; });
    post('/protvc/create', {
      drive_link: S.link || '',
      name: ($('#f-name').value || '').trim(),
      price_note: ($('#f-price').value || '').trim(),
      usp: ($('#f-usp').value || '').trim(),
      hotline: ($('#f-hotline').value || '').trim()
    }).then(function (r) {
      if (!r.ok || !r.data.project_id) throw new Error((r.data && r.data.detail) || 'Không tạo được dự án.');
      S.pid = r.data.project_id; S.tid = r.data.topic_id;
      return pool(ids, function (id) {
        var im = byId[id] || {};
        return post('/projects/' + S.pid + '/drive/import-one', { file_id: id, name: im.name || 'image.jpg' });
      }, 5, function (d, n) { genMsg('import', d + '/' + n); });
    }).then(function () {
      genStep('import', 'done'); genStep('analyze', 'act');
      return post('/projects/' + S.pid + '/analyze', {});
    }).then(function () {
      genStep('analyze', 'done'); genStep('script', 'act');
      return post('/projects/' + S.pid + '/topics/' + S.tid + '/script',
                  { duration_seconds: S.dur, style: S.tvcStyle || '' });
    }).then(function (r) {
      if (!r.ok || !r.data.script) throw new Error((r.data && r.data.detail) || 'Không tạo được kịch bản.');
      genStep('script', 'done');
      S.script = r.data.script;
      setTimeout(function () { ov.hidden = true; creating = false; showReview(S.script); }, 350);
    }).catch(function (e) {
      ov.hidden = true; creating = false;
      alert('Lỗi: ' + (e.message || e));
    });
  };

  /* ---------- STEP 3: review + produce ---------- */
  function showReview(script) {
    var body = $('#review-body'); body.innerHTML = '';
    var segs = (script.segments || script.scenes || []);
    segs.forEach(function (s) {
      var kind = s.kind || (s.scene ? 'cảnh ' + s.scene : 'cảnh');
      var hl = (s.on_screen_text && s.on_screen_text.headline_caps) || s.caption || s.title || '';
      var vo = s.voiceover_vi || s.voiceover || '';
      var dur = s.duration_seconds || '';
      var el = document.createElement('div'); el.className = 'seg';
      el.innerHTML = '<div class="sh"><span class="stag">' + esc(kind) + '</span><span class="sdur">' + (dur ? dur + 's' : '') + '</span></div>'
        + (hl ? '<p class="shl">' + esc(hl) + '</p>' : '') + '<p class="svo">' + esc(vo) + '</p>';
      body.appendChild(el);
    });
    $('#review-modal').hidden = false;
  }
  $('#review-close').onclick = function () { $('#review-modal').hidden = true; };
  $('#review-regen').onclick = function () { $('#review-modal').hidden = true; $('#btn-create').onclick(); };
  $('#review-produce').onclick = function () {
    var b = this; if (b.disabled) return; b.disabled = true; b.textContent = 'Đang khởi tạo dựng phim…';
    post('/projects/' + S.pid + '/topics/' + S.tid + '/produce',
      { aspect_ratio: S.aspect, quality: S.quality, video_style: STYLES[S.style].k,
        music_url: S.musicDownload || '', music_attr: S.musicAttr || '',
        subtitles: S.subs || 'on' }
    ).then(function (r) {
      if (!r.ok || !r.data.video_id) throw new Error((r.data && r.data.detail) || 'Không dựng được video.');
      setStep(4);
      location.href = '/video/' + r.data.video_id;
    }).catch(function (e) {
      alert('Lỗi: ' + (e.message || e)); b.disabled = false; b.textContent = '✓ Duyệt & dựng video';
    });
  };

  // debug hook for offline render tests — harmless, never called by the running app
  window.__ptvDemo = function (imgs, bins) {
    S.images = imgs; S.bins = bins || []; autoSelect();
    renderBins(); selectBin('all');
    $('#workspace').hidden = false; $('#actionbar').hidden = false; updateSel(); setStep(2);
  };

  setStep(1);
  updateSel();  // the bar ships with placeholder copy; show the real (empty) state on load
})();
