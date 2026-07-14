/* RETI Studio — luồng "Tạo TVC chuyên nghiệp" (1 nút). Điều phối các API sẵn có. */
(function () {
  "use strict";
  var $ = function (s) { return document.querySelector(s); };

  var STYLES = [
    { k:'cinematic',  t:'Điện ảnh',   d:'Teal-cam',    sw:'linear-gradient(135deg,#123,#1a3a4a 50%,#c86a3a)',   g:'linear-gradient(120deg,rgba(0,40,60,.6),rgba(255,120,50,.4))',   ac:'#ff7a45', fl:'contrast(1.12) saturate(1.1)' },
    { k:'luxury',     t:'Sang trọng', d:'Vàng gold',   sw:'linear-gradient(135deg,#3a2a10,#8a6a2a 60%,#e0b060)',g:'linear-gradient(120deg,rgba(120,80,20,.5),rgba(255,210,120,.45))',ac:'#e8b45a', fl:'saturate(1.05) brightness(1.04)' },
    { k:'modern',     t:'Hiện đại',   d:'Sạch, tươi',  sw:'linear-gradient(135deg,#123a4a,#2a6a7a 60%,#a0d0d8)',g:'linear-gradient(120deg,rgba(40,120,150,.4),rgba(200,240,255,.35))',ac:'#5ac8e0', fl:'saturate(1.2) brightness(1.08)' },
    { k:'warm',       t:'Ấm áp',      d:'Hoàng hôn',   sw:'linear-gradient(135deg,#4a1a10,#a04a20 60%,#f0a050)',g:'linear-gradient(120deg,rgba(150,50,20,.5),rgba(255,180,90,.45))',ac:'#ff9a4d', fl:'saturate(1.2) brightness(1.03)' },
    { k:'minimal',    t:'Tối giản',   d:'Nhạt, thanh', sw:'linear-gradient(135deg,#33383f,#6a7078 60%,#c8ccd0)',g:'linear-gradient(120deg,rgba(200,200,210,.25),rgba(255,255,255,.2))',ac:'#c0c6d0', fl:'saturate(.62) contrast(1.05) brightness(1.06)' },
    { k:'vibrant',    t:'Năng động',  d:'Rực, trẻ',    sw:'linear-gradient(135deg,#5a1040,#c02060 55%,#ff8040)',g:'linear-gradient(120deg,rgba(200,20,90,.45),rgba(255,140,40,.4))',ac:'#ff3b7a', fl:'saturate(1.4) contrast(1.08)' },
    { k:'night',      t:'Đêm / Neon', d:'Tím, sang',   sw:'linear-gradient(135deg,#10102a,#3a2060 55%,#8040c0)',g:'linear-gradient(120deg,rgba(60,20,120,.55),rgba(180,80,255,.4))',ac:'#a45aff', fl:'brightness(.82) saturate(1.35)' },
    { k:'documentary',t:'Tài liệu',   d:'Tự nhiên',    sw:'linear-gradient(135deg,#2a3020,#4a5a30 60%,#90a060)',g:'linear-gradient(120deg,rgba(60,80,30,.35),rgba(200,210,150,.3))',ac:'#9ab060', fl:'contrast(1.05) saturate(1.05)' }
  ];
  var FONTS = [
    { t:'Thanh lịch',  ff:"Georgia,'Times New Roman',serif", it:'italic', w:'500', up:0, ls:'0' },
    { t:'Hiện đại đậm',ff:"system-ui,'Segoe UI',Roboto,sans-serif", it:'normal', w:'800', up:1, ls:'.01em' },
    { t:'Viết tay',    ff:"'Snell Roundhand','Segoe Script','Brush Script MT',cursive", it:'italic', w:'500', up:0, ls:'0' },
    { t:'Cổ điển',     ff:"'Times New Roman',Georgia,serif", it:'normal', w:'600', up:0, ls:'.01em' },
    { t:'Mạnh mẽ',     ff:"'Arial Narrow','Roboto Condensed',system-ui,sans-serif", it:'normal', w:'900', up:1, ls:'.02em' },
    { t:'Tối giản',    ff:"system-ui,'Segoe UI',sans-serif", it:'normal', w:'300', up:1, ls:'.16em' }
  ];
  var MUSIC = [
    { t:'Hùng tráng', d:'Epic', sp:.55 }, { t:'Cảm xúc', d:'Piano', sp:1.0 },
    { t:'Sang trọng', d:'Cinematic', sp:.8 }, { t:'Sôi động', d:'Sự kiện', sp:.42 },
    { t:'Thư giãn', d:'Lofi', sp:.9 }, { t:'Kịch tính', d:'Trailer', sp:.5 },
    { t:'Bay bổng', d:'Ambient', sp:1.1 }, { t:'Tự hào', d:'Orchestra', sp:.65 }
  ];
  var S = { pid:null, tid:null, style:0, font:1, music:0, aspect:'16:9', dur:30, quality:'standard', musicUrl:'', script:null };

  /* ---------- build preset cards ---------- */
  var sc = $('#styles');
  STYLES.forEach(function (s, i) {
    var el = document.createElement('div'); el.className = 'card' + (i === 0 ? ' sel' : '');
    el.innerHTML = '<div class="sw" style="background:' + s.sw + '"></div><div class="t">' + s.t + '</div><div class="d">' + s.d + '</div>';
    el.onclick = function () { one(sc, el); S.style = i; apply(); };
    sc.appendChild(el);
  });
  var fc = $('#fonts');
  FONTS.forEach(function (f, i) {
    var el = document.createElement('div'); el.className = 'card' + (i === 1 ? ' sel' : '');
    var tx = f.up ? 'THE PARKLAND' : 'The Parkland';
    el.innerHTML = '<div class="fontprev" style="font-family:' + f.ff + ';font-style:' + f.it + ';font-weight:' + f.w + ';letter-spacing:' + f.ls + ';text-transform:' + (f.up ? 'uppercase' : 'none') + '">' + tx + '</div><div class="t">' + f.t + '</div>';
    el.onclick = function () { one(fc, el); S.font = i; apply(); };
    fc.appendChild(el);
  });
  document.querySelectorAll('#aspect .chip').forEach(function (c) { c.onclick = function () { one($('#aspect'), c); S.aspect = c.dataset.a; apply(); }; });
  document.querySelectorAll('#dur .chip').forEach(function (c) { c.onclick = function () { one($('#dur'), c); S.dur = +c.dataset.d; apply(); }; });
  document.querySelectorAll('#quality .chip').forEach(function (c) { c.onclick = function () { one($('#quality'), c); S.quality = c.dataset.q; }; });

  function one(cont, el, cls) {
    cont.querySelectorAll('.' + (cls || 'card') + ', .chip').forEach(function (x) { x.classList.remove('sel'); });
    el.classList.add('sel');
  }
  function apply() {
    var s = STYLES[S.style], f = FONTS[S.font];
    document.documentElement.style.setProperty('--accent', s.ac);
    $('#grade').style.background = s.g;
    var vid = $('#pvid'); if (vid) vid.style.filter = s.fl;
    var hl = $('#hl');
    hl.style.fontFamily = f.ff; hl.style.fontStyle = f.it; hl.style.fontWeight = f.w;
    hl.style.letterSpacing = f.ls; hl.style.textTransform = f.up ? 'uppercase' : 'none';
    hl.textContent = f.up ? 'THE PARKLAND' : 'The Parkland';
    $('#badge').textContent = S.aspect + ' · ' + S.dur + 's';
    $('#pv').classList.toggle('vert', S.aspect === '9:16');
  }
  apply();

  /* ---------- real video preview: play sample clip + chosen music ---------- */
  var pvid = $('#pvid'), paudio = $('#paudio'), pv = $('#pv'), pplay = $('#pplay'), pfill = $('#pfill'), pcap = $('#pcap');
  pvid.src = '/static/sample-preview.mp4';
  function togglePlay() {
    if (pvid.paused) {
      pvid.play().catch(function () {});
      if (S.musicUrl) { try { paudio.currentTime = 0; paudio.play().catch(function () {}); } catch (e) {} }
      pv.classList.add('playing'); if (pcap) pcap.innerHTML = '⏸ Đang phát video mẫu · đổi lựa chọn để xem khác biệt';
    } else {
      pvid.pause(); paudio.pause(); pv.classList.remove('playing');
      if (pcap) pcap.innerHTML = '▶ Bấm để xem thử · đổi phong cách/font/nhạc → video mẫu đổi <b>trực tiếp</b>';
    }
  }
  pplay.onclick = togglePlay;
  pvid.onclick = function () { if (pv.classList.contains('playing')) togglePlay(); };
  pvid.ontimeupdate = function () { if (pvid.duration && pfill) pfill.style.width = (pvid.currentTime / pvid.duration * 100) + '%'; };

  /* ---------- music picker modal (Openverse library) ---------- */
  var mModal = $('#music-modal'), mList = $('#music-list'), mQ = $('#music-q');
  var mAudio = new Audio(); mAudio.preload = 'none'; var mNowRow = null, mNowBtn = null;
  var mMood = 'epic', mTimer = null;
  $('#music-pick').onclick = function () { mModal.hidden = false; if (!mList.querySelector('.trk')) loadMusic(); };
  $('#music-close').onclick = function () { stopPrev(); mModal.hidden = true; };
  $('#music-ai').onclick = function () {
    S.musicUrl = ''; S.musicDownload = ''; S.musicName = ''; S.musicAttr = '';
    $('#mp-name').textContent = 'AI tự tạo nhạc theo phong cách';
    $('#mp-sub').textContent = 'Nhấn để chọn từ kho nhạc'; $('#mp-ico').innerHTML = '♪';
    if (paudio) { paudio.pause(); paudio.removeAttribute('src'); }
    stopPrev(); mModal.hidden = true;
  };
  document.querySelectorAll('#music-moods .chip').forEach(function (c) {
    c.onclick = function () { one($('#music-moods'), c); mMood = c.dataset.m; loadMusic(); };
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
        row.innerHTML = (t.image ? '<img class="cover" src="' + t.image + '" loading="lazy" alt="">' : '<div class="cover"></div>')
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
    $('#mp-ico').innerHTML = t.image ? '<img src="' + t.image + '" alt="">' : '♪';
    if (paudio) { paudio.src = t.audio; }
    stopPrev(); mModal.hidden = true;
  }

  /* ---------- helpers ---------- */
  function form(obj) { var fd = new FormData(); for (var k in obj) fd.append(k, obj[k]); return fd; }
  function post(url, obj) { return fetch(url, { method: 'POST', body: obj instanceof FormData ? obj : form(obj || {}) }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, code: r.status, data: d }; }).catch(function () { return { ok: r.ok, code: r.status, data: {} }; }); }); }
  function folderId(link) { var m = String(link).match(/[-\w]{25,}/); return m ? m[0] : ''; }

  /* limited-concurrency map */
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

  /* ---------- STEP 1: import ---------- */
  var importing = false;
  $('#btn-import').onclick = function () {
    if (importing) return;
    var link = ($('#drive-link').value || '').trim();
    var fid = folderId(link);
    if (!fid) { alert('Link Drive chưa đúng. Dán link thư mục Google Drive (…/folders/…).'); return; }
    importing = true;
    var btn = this; btn.disabled = true;
    var prog = $('#import-prog'), msg = $('#import-msg'), bar = $('#import-bar');
    prog.hidden = false; bar.style.width = '6%'; msg.textContent = 'Đang tạo dự án…';

    post('/protvc/create', { drive_link: link }).then(function (r) {
      if (!r.ok || !r.data.project_id) throw new Error((r.data && r.data.detail) || 'Không tạo được dự án.');
      S.pid = r.data.project_id; S.tid = r.data.topic_id;
      msg.textContent = 'Đang đọc thư mục Drive…'; bar.style.width = '14%';
      return post('/projects/' + S.pid + '/drive/list-images', { folder_id: fid });
    }).then(function (r) {
      var imgs = (r.data && r.data.images) || [];
      if (!imgs.length) throw new Error('Thư mục không có ảnh (hoặc chưa mở quyền "Bất kỳ ai có link").');
      msg.textContent = 'Đang nhập 0/' + imgs.length + ' ảnh…';
      return pool(imgs, function (im) {
        return post('/projects/' + S.pid + '/drive/import-one', { file_id: im.id, name: im.name || 'image.jpg' });
      }, 5, function (done, n) {
        bar.style.width = (14 + (done / n) * 82) + '%';
        msg.textContent = 'Đang nhập ' + done + '/' + n + ' ảnh…';
      }).then(function () { return imgs.length; });
    }).then(function (n) {
      bar.style.width = '100%'; msg.textContent = '✓ Đã nhập ' + n + ' ảnh.';
      $('#img-pill').innerHTML = '✓ Đã nhập <b>' + n + ' ảnh</b> · AI sẽ tự chọn cảnh đẹp nhất';
      setTimeout(function () {
        $('#import-panel').hidden = true; $('#editor').hidden = false;
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 500);
    }).catch(function (e) {
      msg.textContent = 'Lỗi: ' + (e.message || e); bar.style.background = '#ff6a6a';
      importing = false; btn.disabled = false;
    });
  };

  /* ---------- STEP 2: generate script ---------- */
  var busy = false;
  $('#btn-create').onclick = function () {
    if (busy || !S.pid) return; busy = true;
    var btn = this, old = btn.innerHTML; btn.disabled = true;
    btn.innerHTML = '<span>AI đang phân tích & viết kịch bản… (~30s)</span>';
    post('/projects/' + S.pid + '/analyze', {}).then(function () {
      return post('/projects/' + S.pid + '/topics/' + S.tid + '/script', { duration_seconds: S.dur });
    }).then(function (r) {
      if (!r.ok || !r.data.script) throw new Error((r.data && r.data.detail) || 'Không tạo được kịch bản.');
      S.script = r.data.script; showReview(S.script);
      busy = false; btn.disabled = false; btn.innerHTML = old;
    }).catch(function (e) {
      alert('Lỗi tạo kịch bản: ' + (e.message || e));
      busy = false; btn.disabled = false; btn.innerHTML = old;
    });
  };

  /* ---------- STEP 3: review + produce ---------- */
  function showReview(script) {
    var body = $('#review-body'); body.innerHTML = '';
    var segs = (script.segments || script.scenes || []);
    segs.forEach(function (s, i) {
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
  function esc(t) { return String(t == null ? '' : t).replace(/[&<>]/g, function (c) { return { '&':'&amp;','<':'&lt;','>':'&gt;' }[c]; }); }
  $('#review-close').onclick = function () { $('#review-modal').hidden = true; };
  $('#review-regen').onclick = function () { $('#review-modal').hidden = true; $('#btn-create').onclick(); };
  $('#review-produce').onclick = function () {
    var b = this; if (b.disabled) return; b.disabled = true; b.textContent = 'Đang khởi tạo dựng phim…';
    post('/projects/' + S.pid + '/topics/' + S.tid + '/produce',
      { aspect_ratio: S.aspect, quality: S.quality, video_style: STYLES[S.style].k,
        music_url: S.musicDownload || '', music_attr: S.musicAttr || '' }
    ).then(function (r) {
      if (!r.ok || !r.data.video_id) throw new Error((r.data && r.data.detail) || 'Không dựng được video.');
      location.href = '/video/' + r.data.video_id;
    }).catch(function (e) {
      alert('Lỗi: ' + (e.message || e)); b.disabled = false; b.textContent = '✓ Duyệt & dựng video';
    });
  };
})();
