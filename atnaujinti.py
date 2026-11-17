import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

with open("nustatymai.json", "r", encoding="utf-8") as f:
    nustatymai = json.load(f)

raktazodziai = [r.strip().lower() for r in nustatymai.get("raktazodziai", ["cnc", "frezavimas", "tekinimas"]) if r.strip()]
visi_rezultatai = {}

antrastes = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "lt-LT,lt;q=0.9"
}

def tikrinti_cvonline(raktazodziai_list):
    rasti = {}
    url = "https://" + "www.cvonline.lt/api/v1/vacancy-search-service/search"
    
    for zodis in raktazodziai_list:
        parametrai = {"limit": 50, "offset": 0, "keywords[]": zodis, "sorting": "LATEST"}
        try:
            atsakas = requests.get(url, params=parametrai, headers=antrastes, timeout=15).json()
            for d in atsakas.get("vacancies", []):
                sk_id = str(d.get("id"))
                if sk_id not in rasti:
                    galioja_iki = d.get("expirationDate", "")[:10] if d.get("expirationDate") else "Nenurodyta"
                    ikeltas = d.get("publishDate", "")[:19] if d.get("publishDate") else ""
                    miestas = d.get("townName") or "Lietuva"
                    rasti[sk_id] = {
                        "id": f"cvo_{sk_id}",
                        "pavadinimas": d.get("positionTitle", "Be pavadinimo"),
                        "imone": d.get("employerName", "Nenurodyta įmonė"),
                        "miestas": miestas,
                        "galioja": galioja_iki,
                        "ikeltas": ikeltas,
                        "nuoroda": "https://" + f"www.cvonline.lt/lt/vacancy/{sk_id}"
                    }
        except Exception as e:
            print(f"Klaida CV-Online ({zodis}): {e}")
            
    sarasas = list(rasti.values())
    sarasas.sort(key=lambda x: x["ikeltas"], reverse=True)
    return sarasas

def tikrinti_cvbankas(raktazodziai_list):
    rasti = {}
    for zodis in raktazodziai_list:
        url = "https://" + f"www.cvbankas.lt/?keyw={zodis}"
        try:
            atsakas = requests.get(url, headers=antrastes, timeout=15)
            soup = BeautifulSoup(atsakas.text, "html.parser")
            nuorodos = soup.find_all("a", class_="list_a")
            
            for a_tag in nuorodos:
                nuoroda = a_tag.get("href", "")
                if not nuoroda:
                    continue
                if not nuoroda.startswith("http"):
                    nuoroda = "https://" + "www.cvbankas.lt" + nuoroda
                    
                sk_id = re.sub(r'\D', '', nuoroda)[-8:] or nuoroda
                tekstas = a_tag.get_text(" | ", strip=True)
                miestas = "Vilnius" if "Vilnius" in tekstas or "Vilniuje" in tekstas else ("Kaunas" if "Kaunas" in tekstas else ("Klaipėda" if "Klaipėda" in tekstas else "Lietuva"))
                
                if sk_id not in rasti:
                    pav_tag = a_tag.find("h3", class_="list_h3")
                    imone_tag = a_tag.find("span", class_="dib mt5")
                    pavadinimas = pav_tag.text.strip() if pav_tag else tekstas[:80]
                    imone = imone_tag.text.strip() if imone_tag else "CVbankas.lt"
                    rasti[sk_id] = {
                        "id": f"cvb_{sk_id}",
                        "pavadinimas": pavadinimas,
                        "imone": imone,
                        "miestas": miestas,
                        "galioja": "Žiūrėti skelbime",
                        "ikeltas": "",
                        "nuoroda": nuoroda
                    }
        except Exception as e:
            print(f"Klaida CVbankas ({zodis}): {e}")
            
    return list(rasti.values())

def tikrinti_cvmarket(raktazodziai_list):
    rasti = {}
    base = "https://" + "www.cvmarket.lt"
    
    for zodis in raktazodziai_list:
        url = base + f"/darbo-skelbimai?op=search&search%5Bkeyword%5D={zodis}"
        try:
            atsakas = requests.get(url, headers=antrastes, timeout=15)
            soup = BeautifulSoup(atsakas.text, "html.parser")
            korteles = soup.find_all("article") or soup.find_all("div", attrs={"data-job-id": True})
            
            for k in korteles:
                a_tag = k.find("a", href=True)
                if not a_tag:
                    continue
                href = a_tag["href"]
                pilna_nuoroda = href if href.startswith("http") else base + href
                sk_id = re.sub(r'\D', '', pilna_nuoroda)[-7:] or pilna_nuoroda
                
                h2_tag = k.find("h2")
                pavadinimas = h2_tag.get_text(strip=True) if h2_tag else a_tag.get_text(" ", strip=True)[:70]
                
                tekstas = k.get_text(" | ", strip=True)
                miestas = "Vilnius" if "Vilnius" in tekstas else ("Kaunas" if "Kaunas" in tekstas else ("Klaipėda" if "Klaipėda" in tekstas else "Lietuva"))
                
                if sk_id not in rasti and len(pavadinimas) > 3:
                    rasti[sk_id] = {
                        "id": f"cvm_{sk_id}",
                        "pavadinimas": pavadinimas,
                        "imone": "CVmarket.lt",
                        "miestas": miestas,
                        "galioja": "Žiūrėti skelbime",
                        "ikeltas": "",
                        "nuoroda": pilna_nuoroda
                    }
        except Exception as e:
            print(f"Klaida CVmarket ({zodis}): {e}")
            
    return list(rasti.values())

visi_rezultatai["CV-Online.lt"] = tikrinti_cvonline(raktazodziai)
visi_rezultatai["CVbankas.lt"] = tikrinti_cvbankas(raktazodziai)
visi_rezultatai["CVmarket.lt"] = tikrinti_cvmarket(raktazodziai)

laikas = datetime.now().strftime("%Y-%m-%d %H:%M")
duomenys_json = json.dumps(visi_rezultatai, ensure_ascii=False)
html_kodas = f"""<!DOCTYPE html>
<html lang="lt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>Darbo Skelbimai</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f5f7; margin: 0; padding: 16px; color: #172b4d; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .filtrai {{ background: #ffffff; padding: 18px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-end; }}
        .laukelis {{ flex: 1; min-width: 220px; }}
        .laukelis label {{ display: block; font-size: 13px; font-weight: bold; margin-bottom: 5px; color: #5e6c84; }}
        .laukelis input {{ width: 100%; padding: 10px; border: 1px solid #dfe1e6; border-radius: 6px; font-size: 15px; box-sizing: border-box; background: #fff; }}
        .portalo-sekcija {{ background: #ffffff; padding: 18px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; overflow-x: auto; }}
        .portalo-pavadinimas {{ font-size: 19px; margin-top: 0; padding-bottom: 10px; border-bottom: 2px solid #ebecf0; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 650px; }}
        th {{ text-align: left; padding: 10px; background: #fafbfc; border-bottom: 2px solid #dfe1e6; font-size: 13px; color: #5e6c84; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid #ebecf0; vertical-align: middle; font-size: 14px; }}
        tr.atidarytas {{ background-color: #f4f5f7; color: #7a869a; }}
        tr.atidarytas a {{ color: #7a869a; }}
        .skelbimo-nuoroda {{ font-weight: 600; color: #0052cc; text-decoration: none; font-size: 15px; display: block; margin-bottom: 4px; }}
        .skelbimo-nuoroda:hover {{ text-decoration: underline; }}
        .imone-info {{ font-size: 12px; color: #6b778c; }}
        .statusas-badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        .naujas {{ background: #e3fcef; color: #006644; }}
        .matytas {{ background: #dfe1e6; color: #42526e; }}
        .pastaba-input {{ width: 100%; padding: 8px; border: 1px solid #dfe1e6; border-radius: 4px; font-size: 13px; box-sizing: border-box; }}
        .pastaba-input:focus {{ border-color: #0052cc; outline: none; background: #fff; }}
        .laikas {{ font-size: 12px; color: #6b778c; margin-bottom: 12px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="laikas">Automatiškai atnaujinta: <strong>{laikas}</strong> (Tikrinama 3 kartus per parą)</div>
    
    <div class="filtrai">
        <div class="laukelis">
            <label>Miestas (keičiasi iškart):</label>
            <input type="text" id="filtras-miestas" value="Vilnius" placeholder="Pvz.: Vilnius (palikite tuščią visiems)" oninput="issaugotiIrFiltruoti()">
        </div>
        <div class="laukelis">
            <label>Filtruoti pagal žodžius (galima per kablelį):</label>
            <input type="text" id="filtras-zodis" placeholder="Pvz.: cnc, operatorius, programuotojas" oninput="issaugotiIrFiltruoti()">
        </div>
    </div>

    <div id="skelbimu-konteineris"></div>
</div>

<script>
    const duomenys = {duomenys_json};

    const issaugotasMiestas = localStorage.getItem('pasirinktas_miestas');
    if (issaugotasMiestas !== null) {{
        document.getElementById('filtras-miestas').value = issaugotasMiestas;
    }}

    function issaugotiIrFiltruoti() {{
        const miestas = document.getElementById('filtras-miestas').value;
        localStorage.setItem('pasirinktas_miestas', miestas);
        atvaizduotiSkelbimus();
    }}

    function gautiAtidarytus() {{ return JSON.parse(localStorage.getItem('atidaryti_skelbimai') || '{{}}'); }}
    function gautiPastabas() {{ return JSON.parse(localStorage.getItem('skelbimu_pastabos') || '{{}}'); }}

    function pazymetiAtidaryta(id) {{
        const atidaryti = gautiAtidarytus();
        atidaryti[id] = true;
        localStorage.setItem('atidaryti_skelbimai', JSON.stringify(atidaryti));
        const eilute = document.getElementById('row_' + id);
        const badge = document.getElementById('badge_' + id);
        if (eilute) eilute.classList.add('atidarytas');
        if (badge) {{ badge.className = 'statusas-badge matytas'; badge.innerText = 'Atidarytas'; }}
    }}

    function issaugotiPastaba(id, tekstas) {{
        const pastabos = gautiPastabas();
        pastabos[id] = tekstas;
        localStorage.setItem('skelbimu_pastabos', JSON.stringify(pastabos));
    }}

    function atvaizduotiSkelbimus() {{
        const konteineris = document.getElementById('skelbimu-konteineris');
        const atidaryti = gautiAtidarytus();
        const pastabos = gautiPastabas();
        const ieskomasMiestas = document.getElementById('filtras-miestas').value.trim().toLowerCase();
        const ieskomasZodis = document.getElementById('filtras-zodis').value.trim().toLowerCase();
        const zodziai = ieskomasZodis.split(',').map(z => z.trim()).filter(z => z);
        
        konteineris.innerHTML = '';

        for (const [portalas, sarasas] of Object.entries(duomenys)) {{
            const filtruotas = sarasas.filter(s => {{
                const tinkaMiestas = !ieskomasMiestas || (s.miestas && (s.miestas.toLowerCase().includes(ieskomasMiestas) || s.miestas.toLowerCase() === 'lietuva'));
                const tinkaZodis = zodziai.length === 0 || zodziai.some(z => s.pavadinimas.toLowerCase().includes(z) || s.imone.toLowerCase().includes(z));
                return tinkaMiestas && tinkaZodis;
            }});

            const sekcija = document.createElement('div');
            sekcija.className = 'portalo-sekcija';
            let eiluciuHtml = '';
            
            if (filtruotas.length === 0) {{
                eiluciuHtml = '<tr><td colspan="4">Pagal pasirinktą miestą ar filtrą skelbimų nėra.</td></tr>';
            }} else {{
                filtruotas.forEach(s => {{
                    const arMatytas = atidaryti[s.id] ? true : false;
                    const klase = arMatytas ? 'atidarytas' : '';
                    const badgeKlase = arMatytas ? 'matytas' : 'naujas';
                    const badgeTekstas = arMatytas ? 'Atidarytas' : 'Naujas';
                    const esamaPastaba = pastabos[s.id] || '';

                    eiluciuHtml += `
                        <tr id="row_${{s.id}}" class="${{klase}}">
                            <td>
                                <a class="skelbimo-nuoroda" href="${{s.nuoroda}}" target="_blank" onclick="pazymetiAtidaryta('${{s.id}}')">${{s.pavadinimas}}</a>
                                <div class="imone-info">🏢 ${{s.imone}} | 📍 ${{s.miestas}}</div>
                            </td>
                            <td>${{s.galioja}}</td>
                            <td><span id="badge_${{s.id}}" class="statusas-badge ${{badgeKlase}}">${{badgeTekstas}}</span></td>
                            <td>
                                <input type="text" class="pastaba-input" placeholder="Rašyti pastabą..." value="${{esamaPastaba.replace(/"/g, '&quot;')}}" oninput="issaugotiPastaba('${{s.id}}', this.value)">
                            </td>
                        </tr>
                    `;
                }});
            }}

            sekcija.innerHTML = `
                <h3 class="portalo-pavadinimas">${{portalas}} (${{filtruotas.length}})</h3>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 42%;">Skelbimas ir nuoroda</th>
                            <th style="width: 15%;">Galioja iki</th>
                            <th style="width: 13%;">Būsena</th>
                            <th style="width: 30%;">Mano pastaba</th>
                        </tr>
                    </thead>
                    <tbody>${{eiluciuHtml}}</tbody>
                </table>
            `;
            konteineris.appendChild(sekcija);
        }}
    }}

    atvaizduotiSkelbimus();
</script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_kodas)

print("Sėkmingai atnaujinta!")
