# Daitsu / TCL Tuya AC – Home Assistant Custom Integration

Maßgeschneiderte Home-Assistant-Integration für **Daitsu Artic Plus** (und baugleiche TCL-Klimaanlagen mit neuem Tuya-WLAN-Stick).

## Enthalten
- **Klima (`climate`)**: Ein/Aus, Raumtemperatur, Soll-Temperatur in `0,5 °C`-Schritten (`16,0–31,0 °C`), alle 5 Modi (*Auto, Kühlen, Entfeuchten, Lüften, Heizen*), alle 8 Lüfterstufen (*Auto, Leise, Sanft, Niedrig, Mittel, Stark, Hoch, Turbo*).
- **Lamellen (`select`)**: Vertikale & horizontale Lamellen mit den exakten Daitsu/TCL-Positionen (`9–13` Fixpositionen + Schwenk-Modi).
- **Optionen (`switch`)**: Display-Licht, Piepton, Eco, AI-Eco, Sanfte Brise, Warmluft-Boost, Ionisator, Anti-Schimmel Trocknen, Selbstreinigung, 8 °C Frostschutz, Zusatzheizung, Frischluftklappe.
- **Sensoren (`sensor`)**: Raumtemperatur (°C), Außentemperatur (`ure`, °C), Kompressor-Frequenz Ist & Soll (Hz), Außenlüfter Drehzahl (rpm), Stromverbrauch (kWh), Fehlerdiagnose.

## Installation in Home Assistant (3 Schritte)
1. Kopiere den kompletten Ordner `custom_components/daitsu_tuya_ac` in dein Home-Assistant-Konfigurationsverzeichnis unter `/config/custom_components/daitsu_tuya_ac` (z. B. per Samba-Share, Studio Code Server oder File Editor).
2. Starte **Home Assistant neu**.
3. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**, suche nach **„Daitsu / TCL Tuya Klimaanlage“** und trage deine Tuya-Cloud-Daten (**Access ID**, **Access Secret**, **Region** und optional **User-ID**) ein.

Optional findest du in `dashboard_example.yaml` eine fertige Dashboard-Karte inkl. Verlaufsgraphen.
