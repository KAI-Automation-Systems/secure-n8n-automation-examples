# Zwei Praxisbeispiele für sichere Automatisierung

Kevin Mast · KAI Automation Systems

Diese Beispiele wurden neu für mein Portfolio entwickelt. Sie zeigen einen möglichen technischen Ansatz für Projekte eines Automatisierungsbüros; sie sind keine Referenzen abgeschlossener Kundenaufträge.

## Anfragen vorsortieren und kontrolliert weiterbearbeiten

Ein Team erhält wiederkehrende Anfragen zu Rechnungen, technischen Problemen und allgemeinen Themen. Ein authentifizierter n8n-Workflow nimmt die Anfrage entgegen. Der lokale Dienst leitet daraus drei Ja/Nein-Signale ab. Nur diese Signale können optional an ein Sprachmodell gehen. Namen, Betreff und Nachrichtentext werden weder an das Modell gesendet noch in der Datenbank gespeichert.

Das Ergebnis ist ein Vorschlag für Kategorie und Priorität. Unpassende Modellausgaben und Ausfälle führen in die manuelle Prüfung. Ein Mensch entscheidet über die Freigabe. Der Workflow verschickt keine Nachricht und löst keine weiteren Aktionen aus.

**Was daran relevant ist:** n8n-Orchestrierung, REST-Integration, klare Datenbegrenzung, kontrollierte LLM-Ausgabe und nachvollziehbare menschliche Freigabe. Für diese einfache Einteilung reicht auch die mitgelieferte regelbasierte Variante; der Modelleinsatz ist bewusst optional.

## Rechnungsdaten prüfen und Freigaben nachvollziehbar steuern

Ein zweiter n8n-Workflow übernimmt strukturierte Rechnungsdaten. Der Dienst prüft Währung, Zahlenformat und Summen mit ganzzahligen Centbeträgen. Doppelte Ereignisse erzeugen keinen zweiten Auftrag. Dieselbe Lieferanten- und Rechnungsreferenz darf nicht unter einer neuen Ereignis-ID erneut angelegt werden.

Ab EUR 1.000 sind zwei unterschiedliche Reviewer erforderlich. Derselbe Reviewer kann die zweite Freigabe nicht durch wiederholtes Klicken ersetzen. Entscheidungen werden in derselben Datenbanktransaktion wie der Status gespeichert und mit einem HMAC-signierten Auditereignis ergänzt.

**Was daran relevant ist:** SQL, Transaktionen, Fehlerfälle, Idempotenz und getrennte Berechtigungen. Es gibt keine Zahlungsauslösung und keine Behauptung einer steuerrechtlichen Rechnungsprüfung.

## Bewusste Grenzen

Die Beispiele laufen lokal, nutzen synthetische Daten und sind kein öffentlich erreichbarer Produktivdienst. Für einen Kundeneinsatz wären unter anderem Identitätsverwaltung, TLS, Betriebsüberwachung, Mandantentrennung, Aufbewahrung und Datenschutzvereinbarungen projektspezifisch zu klären. Tests und tatsächlich durchgeführte Prüfungen stehen in `docs/VALIDATION.md`.

Technische Details, Startanleitung und importierbare Workflows befinden sich in der [README](README.md).
