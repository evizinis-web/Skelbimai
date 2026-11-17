import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

with open("nustatymai.json", "r", encoding="utf-8") as f:
    nustatymai = json.load(f)

svetaines = nustatymai.get("svetaines", [])
raktazodziai = [r.strip().lower() for r in nustatymai.get("raktazodziai", []) if r.strip()]
visi_rezultatai = {}

def tikrinti_cvonline(raktazodziai_list):
    rasti = {}
    url = "https://" + "www.cvonline.lt/api/v1/vacancy-search-service/search"
    antrastes = {"User-Agent": "Mozilla/5.0"}
    
    for zodis in raktazodziai_list:
        parametrai = {"limit": 30, "offset": 0, "keywords[]": zodis, "sorting": "LATEST"}
        try:
            atsakas = requests.get(url, params=parametrai, headers=antrastes, timeout=15).json()
            for d in atsakas.get("vacancies", []):
                sk_id = str(d.get("id"))
                if sk_id not in rasti:
                    galioja_iki = d.get("expirationDate", "")[:10] if d.get("expirationDate") else "Nenurodyta"
                    ikeltas = d.get("publishDate", "")[:19] if d.get("publishDate") else ""
                    rasti[sk_id] = {
                        "id": f"cvo_{sk_id}",
                        "pavadinimas": d.get("positionTitle", "Be pavadinimo"),
                        "imone": d.get("employerName", "Nenurodyta įmonė"),
                        "miestas": d.get("townName", "Lietuva"),
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
    antrastes = {"User-Agent": "Mozilla/5.0"}
    
    for zodis in raktazodziai_list:
        url = "https://" + f"www.cvbankas.lt/?keyw={zodis}"
        try:
            atsakas = requests.get(url, headers=antrastes, timeout=15)
            soup = BeautifulSoup(atsakas.text, "html.parser")
            straipsniai = soup.find_all("article", class_="list_article")
            
            for art in straipsniai:
                a_tag = art.find("a", class_="list_a")
                if not a_tag:
                    continue
                nuoroda = a_tag["href"]
                sk_id = re.sub(r'\D', '', nuoroda)[-8:] or nuoroda
                
                if sk_id not in rasti:
                    pav_tag = art.find("h3", class_="list_h3")
                    imone_tag = art.find("span", class_="dib mt5")
                    miestas_tag = art.find("span", class_="list_city")
                    laikas_tag = art.find("span", class_="txt_list_2")
                    
                    rasti[sk_id] = {
                        "id": f"cvb_{sk_id}",
                        "pavadinimas": pav_tag.text.strip() if pav_tag else "Be pavadinimo",
                        "imone": imone_tag.text.strip() if imone_tag else "Nenurodyta įmonė",
                        "miestas": miestas_tag.text.strip() if miestas_tag else "Lietuva",
                        "galioja": laikas_tag.text.strip() if laikas_tag else "Žiūrėti skelbime",
                        "ikeltas": "",
                        "nuoroda": nuoroda
                    }
        except Exception as e:
            print(f"Klaida CVbankas ({zodis}): {e}")
            
    return list(rasti.values())

for svetaine in svetaines:
    sv_lower = svetaine.lower()
    if "cvonline.lt" in sv_lower:
        visi_rezultatai["CV-Online.lt"] = tikrinti_cvonline(raktazodziai)
    elif "cvbankas.lt" in sv_lower:
        visi_rezultatai["CVbankas.lt"] = tikrinti_cvbankas(raktazodziai)
    else:
        visi_rezultatai[svetaine] = []

laikas = datetime.now().strftime("%Y-%m-%d %H:%M")
svetaines_str = ", ".join(svetaines)
raktazodziai_str = ", ".join(raktazodziai)
duomenys_json = json.dumps(visi_rezultatai, ensure_ascii=False)
html_dalis_1 = f"""<!DOCTYPE html>
<html lang="lt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Darbo Skelbimų Sistema</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f5f7; margin: 0; padding: 20px; color: #172b4d; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .valdymo-lentele {{ background: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; }}
        .valdymo-lentele h2 {{ margin-top: 0; font-size: 18px; color: #0052cc; }}
        .laukeliu-grupe {{ display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 15px; }}
        .laukelis {{ flex: 1; min-width: 250px; }}
        .laukelis label {{ display: block; font-size: 13px; font-weight: bold; margin-bottom: 5px; color: #5e6c84; }}
        .laukelis input {{ width: 100%; padding: 10px; border: 1px solid #dfe1e6; border-radius: 6px; font-size: 14px; box-sizing: border-box; }}
        .mygtukas {{ background: #0052cc; color: white; border: none; padding: 11px 20px; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; }}
        .mygtukas:hover {{ background: #0747a6; }}
        .instrukcija-box {{ display: none; background: #e3fcef; border: 1px solid #36b37e; padding: 15px; border-radius: 6px; margin-top: 15px; font-size: 14px; }}
        textarea {{ width: 100%; height: 90px; margin-top: 8px; font-family: monospace; font-size: 12px; padding: 8px; box-sizing: border-box; }}
        .portalo-sekcija {{ background: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; overflow-x: auto; }}
        .portalo-pavadinimas {{ font-size: 20px; margin-top: 0; padding-bottom: 10px; border-bottom: 2px solid #ebecf0; color: #172b4d; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 700px; }}
        th {{ text-align: left; padding: 12px; background: #fafbfc; border-bottom: 2px solid #dfe1e6; font-size: 13px; color: #5e6c84; }}
        td {{ padding: 12px; border-bottom: 1px solid #ebecf0; vertical-align: middle; font-size: 14px; }}
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
        .atnaujinta-laikas {{ font-size: 12px; color: #6b778c; margin-bottom: 15px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="atnaujinta-laikas">Automatiškai atnaujinta: <strong>{laikas}</strong> (Tikrinama 3 kartus per parą)</div>
    <div class="valdymo-lentele">
        <h2>Paieškos nustatymai</h2>
        <div class="laukeliu-grupe">
            <div class="laukelis">
                <label>Tikrinami tinklapiai (atskirkite kableliu):</label>
                <input type="text" id="input-svetaines" value="{svetaines_str}">
            </div>
            <div class="laukelis">
                <label>Raktažodžiai (atskirkite kableliu):</label>
                <input type="text" id="input-raktazodziai" value="{raktazodziai_str}">
            </div>
        </div>
        <button class="mygtukas" onclick="paruostiAtnaujinima()">Atnaujinti nustatymus</button>
        <div id="instrukcija-box" class="instrukcija-box">
            <strong>Kaip išsaugoti naujus nustatymus:</strong> Nukopijuokite žemiau esantį tekstą, atsidarykite savo GitHub projekte failą <code>nustatymai.json</code> ir įklijuokite jį vietoj seno teksto.
            <textarea id="json-rezultatas" readonly></textarea>
            <button class="mygtukas" style="margin-top:8px; background:#36b37e;" onclick="kopijuotiIrAtidaryti()">Kopijuoti ir atidaryti GitHub</button>
        </div>
    </div>
    <div id="skelbimu-konteineris"></div>
</div>
"""
html_dalis_2 = f"""
<script>
    const duomenys = {duomenys_json};

    function gautiAtidarytus() {{
        return JSON.parse(localStorage.getItem('atidaryti_skelbimai') || '{{}}');
    }}

    function gautiPastabas() {{
        return JSON.parse(localStorage.getItem('skelbimu_pastabos') || '{{}}');
    }}

    function pazymetiAtidaryta(id) {{
        const atidaryti = gautiAtidarytus();
        atidaryti[id] = true;
        localStorage.setItem('atidaryti_skelbimai', JSON.stringify(atidaryti));
        const eilute = document.getElementById('row_' + id);
        const badge = document.getElementById('badge_' + id);
        if (eilute) eilute.classList.add('atidarytas');
        if (badge) {{
            badge.className = 'statusas-badge matytas';
            badge.innerText = 'Atidarytas';
        }}
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
        konteineris.innerHTML = '';

        for (const [portalas, sarasas] of Object.entries(duomenys)) {{
            const sekcija = document.createElement('div');
            sekcija.className = 'portalo-sekcija';
            let eiluciuHtml = '';
            
            if (sarasas.length === 0) {{
                eiluciuHtml = '<tr><td colspan="4">Pagal šiuos raktažodžius skelbimų nerasta arba svetainė dar nepalaikoma.</td></tr>';
            }} else {{
                sarasas.forEach(s => {{
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
                <h3 class="portalo-pavadinimas">${{portalas}} (${{sarasas.length}})</h3>
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

    function paruostiAtnaujinima() {{
        const svTekstas = document.getElementById('input-svetaines').value;
        const rkTekstas = document.getElementById('input-raktazodziai').value;
        const obj = {{
            svetaines: svTekstas.split(',').map(s => s.trim()).filter(s => s),
            raktazodziai: rkTekstas.split(',').map(r => r.trim()).filter(r => r)
        }};
        document.getElementById('json-rezultatas').value = JSON.stringify(obj, null, 2);
        document.getElementById('instrukcija-box').style.display = 'block';
    }}

    function kopijuotiIrAtidaryti() {{
        const tekstas = document.getElementById('json-rezultatas');
        tekstas.select();
        document.execCommand('copy');
        alert('Nustatymai nukopijuoti! Atsidariusiame lange paspauskite pieštuko ikoną (Edit), įklijuokite tekstą ir paspauskite Commit changes.');
        window.open('https://github.com', '_blank');
    }}

    atvaizduotiSkelbimus();
</script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_dalis_1 + html_dalis_2)

print("Sėkmingai sugeneruotas naujas index.html!")
