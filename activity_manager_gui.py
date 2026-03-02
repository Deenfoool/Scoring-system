import webview, json, os

DB = 'activity_links_webview.json'

class Api:
    def __init__(self):
        self.data = {"types": {}, "profile": {"me": "", "lvl": "", "chk": "", "goal": 300}}
        self.last = []
        if os.path.exists(DB):
            try:
                with open(DB, 'r', encoding='utf-8') as f: self.data.update(json.load(f))
            except: pass

    def save(self):
        with open(DB, 'w', encoding='utf-8') as f: json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_info(self):
        types = [{"id": k, **v, "u": len([l for l in v.get('links', []) if not l['used']])} for k, v in self.data["types"].items()]
        # Для общей статы считаем новости по номиналу (или как тебе удобнее видеть в запасе)
        pts = sum(t['u'] * t['points'] for t in types)
        return {"types": types, "points": pts, "count": sum(t['u'] for t in types), "profile": self.data["profile"]}

    def add_links(self, text):
        links = [l.strip() for l in text.splitlines() if l.strip()]
        added, unknown = 0, []
        exist = set(l['url'] for info in self.data["types"].values() for l in info.get('links', []))
        for l in links:
            p = l.split('/')
            ncs = p[5] if len(p) >= 6 else None
            if not ncs: continue
            if l not in exist:
                if ncs not in self.data["types"]: (unknown.append(ncs) if ncs not in unknown else None)
                else: self.data["types"][ncs].setdefault('links', []).append({"url": l, "used": False}); added += 1
        self.save(); return {"added": added, "unknown": unknown}

    def manage_type(self, nid, desc, pts, news, delete=False):
        if delete: self.data["types"].pop(nid, None)
        else: self.data["types"][nid] = {"description": desc, "points": int(pts), "is_news": news, "links": self.data["types"].get(nid, {}).get('links', [])}
        self.save(); return True

    def get_available_news(self, target):
        limit = int(target) / 2
        news_list = []
        for nid, info in self.data["types"].items():
            if info['is_news']:
                for l in info['links']:
                    if not l['used']:
                        # ЛОГИКА: Если новость больше лимита, она дает лимит. Если меньше - дает номинал.
                        effective_pts = min(info['points'], limit)
                        news_list.append({
                            "url": l['url'],
                            "pts": effective_pts,
                            "nominal": info['points'],
                            "desc": info['description']
                        })
        return news_list

    def gen_report(self, target, me, lvl, chk, selected_news_url=None):
        target = int(target)
        limit = target / 2
        r_links = []
        for nid, info in self.data["types"].items():
            if not info['is_news']:
                for l in info['links']:
                    if not l['used']:
                        r_links.append({"url": l['url'], "pts": info['points'], "nid": nid})
       
        sel_news = None
        n_pts = 0
        if selected_news_url:
            for nid, info in self.data["types"].items():
                if info['is_news']:
                    for l in info['links']:
                        if l['url'] == selected_news_url:
                            # Та же логика расчета баллов новости в отчет
                            n_pts = min(info['points'], limit)
                            sel_news = {"url": l['url'], "pts": n_pts, "nid": nid}
                            break

        needed_reg = max(0, target - n_pts)
        r_links.sort(key=lambda x: x['pts'], reverse=True)
        sel_r, r_val = [], 0
        for r in r_links:
            if r_val < needed_reg:
                sel_r.append(r)
                r_val += r['pts']

        if (n_pts + r_val) < target:
            return {"success": False, "msg": f"Не хватает {int(target-(n_pts+r_val))} баллов!"}
       
        res_list = sel_r + ([sel_news] if sel_news else [])
        self.last = [i['url'] for i in res_list]
        for i in res_list:
            for l in self.data["types"][i['nid']]['links']:
                if l['url'] == i['url']: l['used'] = True
       
        self.data["profile"].update({"me":me,"lvl":lvl,"chk":chk,"goal":target})
        self.save()

        res = f"Форма заполнения отчета на повышение:\n\n1) {me}\n2) {lvl}\n"
        if sel_r: res += f"3.1) Обычные активности, {int(r_val)} баллов\n" + "\n".join(i['url'] for i in sel_r) + "\n"
        if sel_news: res += f"3.2) Новость, {int(n_pts)} баллов\n{sel_news['url']}\n"
        res += f"4) {chk}"
        return {"success": True, "report": res}

    def rollback(self):
        for u in self.last:
            for n in self.data["types"]:
                for l in self.data["types"][n].get('links', []):
                    if l['url'] == u: l['used'] = False
        self.last = []; self.save(); return True

    def clear_used(self):
        for nid in self.data["types"]: self.data["types"][nid]['links'] = [l for l in self.data["types"][nid].get('links', []) if not l['used']]
        self.save(); return True

api = Api()
html = '''
<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    :root { --bg: #202225; --side: #2f3136; --card: #36393f; --accent: #5865f2; --success: #43b581; --danger: #f04747; --text: #dcddde; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; height: 100vh; overflow: hidden; }
    .side { width: 250px; background: var(--side); display: flex; flex-direction: column; border-right: 1px solid #18191c; }
    .nav-btn { width: 90%; padding: 12px; border: none; background: transparent; color: #8e9297; cursor: pointer; text-align: left; border-radius: 4px; margin: 4px auto; font-weight: 500; font-size: 15px; }
    .nav-btn:hover { background: #393c43; color: #dcddde; }
    .nav-btn.active { background: #4f545c; color: #fff; }
    .main { flex: 1; padding: 30px; overflow-y: auto; background: #36393f; }
    .card { background: #2f3136; padding: 25px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    input, textarea, select { width: 100%; background: #202225; border: 1px solid #202225; color: #fff; padding: 12px; border-radius: 4px; margin-bottom: 12px; outline: none; font-size: 14px; }
    input:focus { border-color: var(--accent); }
    .btn { padding: 12px 20px; border-radius: 4px; border: none; cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; transition: 0.2s; }
    .btn:active { transform: translateY(1px); }
    .btn-p { background: var(--accent); color: #fff; } .btn-p:hover { background: #4752c4; }
    .btn-s { background: var(--success); color: #fff; }
    .btn-d { background: var(--danger); color: #fff; }
    .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); display: none; align-items: center; justify-content: center; z-index: 1000; }
    pre { background: #202225; padding: 20px; border-radius: 5px; white-space: pre-wrap; font-size: 13px; line-height: 1.6; border: 1px solid #18191c; color: #b9bbbe; }
</style></head><body>

<div id="newsModal" class="modal">
    <div class="card" style="width: 450px;">
        <h3 style="margin-top:0">Выбор новости</h3>
        <p style="font-size: 13px; color: #b9bbbe;">Если баллы новости > 50% от цели, они будут урезаны до 50% лимита автоматически.</p>
        <select id="newsSelect"></select>
        <div style="display:flex; gap:10px; margin-top:15px">
            <button class="btn btn-p" style="flex:1" onclick="confirmGen()">Сформировать</button>
            <button class="btn btn-d" onclick="closeModal()">Отмена</button>
        </div>
    </div>
</div>

<div class="side">
    <div style="padding:25px; font-weight:800; color:#fff; font-size:18px; letter-spacing:1px">ACTIVITY v4.4</div>
    <div style="flex:1; padding-top:10px">
        <button class="nav-btn active" onclick="tab('add',this)">📥 Загрузка ссылок</button>
        <button class="nav-btn" onclick="tab('gen',this)">📄 Создать отчет</button>
        <button class="nav-btn" onclick="tab('set',this)">⚙️ Управление базой</button>
    </div>
    <div style="padding:20px; background: #292b2f; border-top: 1px solid #202225">
        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:5px">
            <span>Прогресс до цели</span>
            <span id="gt">0/300</span>
        </div>
        <div style="background:#40444b; height:6px; border-radius:3px; overflow:hidden">
            <div id="bf" style="background:var(--accent); height:100%; width:0%; transition:0.5s"></div>
        </div>
        <input id="gl" type="number" oninput="upd()" style="margin-top:10px; padding:6px; font-size:12px">
    </div>
</div>

<div class="main">
    <div id="add" class="tab">
        <div class="card">
            <h3 style="margin-top:0">Вставить ссылки</h3>
            <textarea id="ti" rows="12" placeholder="Вставьте ссылки из каналов Discord..."></textarea>
            <button class="btn btn-p" onclick="addL()">➕ Добавить в базу данных</button>
        </div>
    </div>
   
    <div id="gen" class="tab" style="display:none">
        <div class="card">
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px">
                <div><label style="font-size:12px">НУЖНО БАЛЛОВ</label><input id="tg" type="number" placeholder="Напр: 300"></div>
                <div><label style="font-size:12px">ВАШ НИК</label><input id="mt" placeholder="@Nickname"></div>
                <div><label style="font-size:12px">ВАШ РАНГ</label><input id="lv" placeholder="2-3"></div>
                <div><label style="font-size:12px">ПРОВЕРЯЮЩИЙ</label><input id="ct" placeholder="@High_MA"></div>
            </div>
            <button class="btn btn-p" style="width:100%; margin: 10px 0" onclick="openNewsModal()">🚀 Сформировать отчет</button>
            <div style="display:flex; gap:10px; margin-bottom:15px">
                <button class="btn btn-s" onclick="copy()">📋 Копировать текст</button>
                <button id="rb" class="btn btn-d" onclick="roll()" style="display:none">↩️ Отменить (Откат)</button>
            </div>
            <pre id="out"></pre>
        </div>
    </div>

    <div id="set" class="tab" style="display:none">
        <div class="card">
            <h3>Активные каналы в базе</h3>
            <div id="tl"></div>
            <button class="btn btn-d" style="width:100%; margin-top:20px" onclick="clearU()">🧹 Очистить использованные ссылки</button>
        </div>
    </div>
</div>

<script>
    async function upd() {
        const s = await pywebview.api.get_info();
        const g = document.getElementById('gl').value || 1;
        const p = Math.min(100, (s.points / g) * 100);
        document.getElementById('bf').style.width = p + '%';
        document.getElementById('gt').innerText = s.points + ' / ' + g;
    }

    async function openNewsModal() {
        if(!tg.value) { alert("Укажите цель баллов!"); return; }
        const news = await pywebview.api.get_available_news(tg.value);
        const sel = document.getElementById('newsSelect');
        sel.innerHTML = '<option value="">-- Без новости (только обычные) --</option>';
        news.forEach(n => {
            const label = n.nominal > n.pts ? `${n.desc} (${n.nominal} -> ${n.pts}б лимит)` : `${n.desc} (${n.pts}б)`;
            sel.innerHTML += `<option value="${n.url}">${label}</option>`;
        });
        document.getElementById('newsModal').style.display = 'flex';
    }

    function closeModal() { document.getElementById('newsModal').style.display = 'none'; }

    async function confirmGen() {
        const newsUrl = document.getElementById('newsSelect').value;
        closeModal();
        const r = await pywebview.api.gen_report(tg.value, mt.value, lv.value, ct.value, newsUrl);
        if(r.success) { out.innerText = r.report; rb.style.display='inline-flex'; upd(); } else alert(r.msg);
    }

    function tab(id, el) {
        document.querySelectorAll('.tab').forEach(t => t.style.display = 'none');
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(id).style.display = 'block';
        el.classList.add('active'); if(id === 'set') loadT();
    }

    async function addL() {
        const r = await pywebview.api.add_links(ti.value);
        if(r.unknown.length) {
            for(let id of r.unknown) {
                const d = prompt("Название для канала " + id + ":"), p = prompt("Баллы за ссылку:"), n = prompt("Это новость? (Да/Нет)");
                if(d && p) await pywebview.api.manage_type(id, d, p, (n||"").toLowerCase().includes("да"));
            }
            return addL();
        }
        ti.value = ''; upd(); alert("Ссылки успешно добавлены!");
    }

    function copy() {
        const el = document.createElement('textarea'); el.value = out.innerText;
        document.body.appendChild(el); el.select(); document.execCommand('copy');
        document.body.removeChild(el); alert("Отчет скопирован!");
    }

    async function loadT() {
        const s = await pywebview.api.get_info();
        tl.innerHTML = s.types.map(t => `<div style="display:flex; justify-content:space-between; padding:12px; background:#202225; border-radius:4px; margin-bottom:6px; align-items:center">
            <span><b>${t.description}</b> (${t.points}б) ${t.is_news ? '⭐' : ''} <small style="color:#72767d; margin-left:10px">${t.u} шт.</small></span>
            <button class="btn btn-d" style="padding:5px 10px" onclick="delT('${t.id}')">✕</button></div>`).join('');
    }

    async function delT(id) { if(confirm("Удалить этот канал и все его ссылки?")) { await pywebview.api.manage_type(id,0,0,0,true); loadT(); upd(); } }
    async function clearU() { if(confirm("Удалить из базы все ссылки, которые уже были в отчетах?")) { await pywebview.api.clear_used(); upd(); } }
    async function roll() { if(await pywebview.api.rollback()){ out.innerText=""; rb.style.display='none'; upd(); alert("Баллы возвращены в базу."); } }

    window.addEventListener('pywebviewready', async () => {
        const s = await pywebview.api.get_info();
        mt.value = s.profile.me || ""; lv.value = s.profile.lvl || "";
        ct.value = s.profile.chk || ""; gl.value = s.profile.goal || 300;
        upd();
    });
</script></body></html>
'''  # This is the missing closing triple quote

# Start the webview application
if __name__ == "__main__":
    webview.create_window('Activity Manager', html=html, js_api=api, width=1000, height=700)
    webview.start(debug=True)
